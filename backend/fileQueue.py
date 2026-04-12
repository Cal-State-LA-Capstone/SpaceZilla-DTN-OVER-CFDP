import os
import threading
import time

import pyion

# used to keep track of files in the queue
counter = 0

# holds files
queue = []

# avoid threads crashing
queueLock = threading.Lock()

# keep track of background thread
sendThread = None

# cfpd entity returned by cfpd_open(), used for transfering
entity = None
proxy = None
bpProxy = None

# destination
endPoint = None

# stores callback func to know when the status changes
statusChange = None

# Id of the file being sent
activeId = None

# used so active_id doesn't crash
activeLock = threading.Lock()

paused = False
pauseEvent = threading.Event()
pauseEvent.set()



# Increments counter by 1 for everyy new file added to the queue
def nextId():
    global counter
    counter += 1
    return str(counter)


# This sets up the connection between nodes
def fileQueue(nodeNumber: int, entityId: int, bpEndpoint: str):
    global proxy, bpProxy, endpoint, entity
    os.makedirs("/app/SZ_received_files", exist_ok=True)
    proxy = pyion.get_cfdp_proxy(nodeNumber)
    bpProxy = pyion.get_bp_proxy(nodeNumber)
    endpoint = bpProxy.bp_open(bpEndpoint)
    entity = proxy.cfdp_open(entityId, endpoint)


# takes the file path and adds it to the queue as a dictionary
def queueFile(filePath):
    ids = []
    with queueLock:
        for path in filePath:
            queueId = nextId()
            queue.append(
                {
                    "id": queueId,
                    "path": path,
                    "fileName": os.path.basename(path),
                    "size": os.path.getsize(path) if os.path.exists(path) else 0,
                    "status": "Queued",
                }
            )
            ids.append(queueId)
    return ids


# uses the queueId to remove a file from the queue before its sent
#can be tweaked so that it removes the cancelled
#file from the queue completely
#def removeFile(queueId):
 #   with queueLock:
  #      for i, item in enumerate(queue):
   #         if item["id"] == queueId:
    #            if item["status"] == "Running":
     #               return False
      #          queue.pop(i)
       #         return True
    #return False

# uses background thread to send the files.
# Stores 'onChange' so we can get status updates.
# also checks for other threads.
def sendFiles(onChange):
    global sendThread, statusChange
    print("entity in sendFiles:", entity)
    if sendThread and sendThread.is_alive():
        return
    statusChange = onChange
    sendThread = threading.Thread(target=processQueue, daemon=True)
    sendThread.start()

#Our own implementation of suspend/cancel/resume that will
#work on the queued files. Any file that has
#already started sending will not be affected

def suspend(queueId):
    with queueLock:
        item = getItemById(queueId)
        if item and item["status"] == "Queued":
            item["status"] = "Suspended"
    print(f"File {queueId} suspended.")
    return 0

def cancel(queueId):
    with queueLock:
        for item in queue:
            if item["id"] == queueId and item["status"] == "Queued":
                item["status"] = "Cancelled"
    pauseEvent.set()
    print(f"File {queueId} cancelled.")
    return 0

def resume(queueId):
    global sendThread
    with queueLock:
        item = getItemById(queueId)
        if item and item["status"] == "Suspended":
            item["status"] = "Queued"
    if sendThread is None or not sendThread.is_alive():
        sendThread = threading.Thread(target=processQueue, daemon=True)
        sendThread.start()
    print(f"File {queueId} resumed.")
    return 0

##################


# searches queue for a specific item in the queue by its ID. If we find it
# it seturns the dictionary for that ID. 'updateStatus' and statusIndicator' use this
def getItemById(queueId):
    for item in queue:
        if item["id"] == queueId:
            return item
    return None


# updates the file status in the queue and chages the 'statusChange'  variable
def updateStatus(queueId, status):
    with queueLock:
        item = getItemById(queueId)
        if item:
            item["status"] = status
    if statusChange:
        statusChange(queueId, status)


# cfpd event handler thasts connected to a 'queueId'
def makeEvent(queueId):
    def handler(event):
        eventName = str(event)
        if "FINISHED" in eventName:
            if hasattr(event, "condition_code") and event.condition_code != 0:
                updateStatus(queueId, "Failed")
            else:
                updateStatus(queueId, "Completed")
        elif "FAULT" in eventName or "ABANDONED" in eventName:
            updateStatus(queueId, "Failed")
        elif "SUSPENDED" in eventName:
            updateStatus(queueId, "Queued")
        elif "RESUMED" in eventName:
            updateStatus(queueId, "Running")

    return handler


# this is used for the send thread. It loops through queue looking for the next
# file added to the queue. If it finds one it will change the status to 'Running'
# and register the event handler and it will call 'cfdp_send'.
# This will keep going until the queue is empty.
def processQueue():
    global activeId
    print("Testing process queueu")
    while True:
        #sleep if paused
        pauseEvent.wait()
        with queueLock:
            nextItem = next(
                (item.copy() for item in queue if item["status"] == "Queued"), None
            )

        print("next Item: ",nextItem)
        print("queue: ", queue)
        if nextItem is None:
            break

        queueId = nextItem["id"]
        path = nextItem["path"]
        filename = nextItem["fileName"]

        with activeLock:
            activeId = queueId
        updateStatus(queueId, "Running")

        try:
            print(f"event handler for: ,{filename}")
            entity.register_event_handler("CFDP_ALL_EVENTS", makeEvent(queueId))
            print(f"cfdp_send for {path}")
            entity.cfdp_send(
                source_file=path, dest_file=f"/SZ_received_files/{filename}"
            )
            print("send done,waiting to end")
            success = entity.wait_for_transaction_end()
            print(f"transaction end: {success}")
            time.sleep(3)

            if success:
                updateStatus(queueId,"Completed")
            else:
                updateStatus(queueId,"Failed")

        except Exception as e:
            print(f"Couldn't send {filename}: {e}")
            updateStatus(queueId, "Failed")

        with activeLock:
            activeId = None
