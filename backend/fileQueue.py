import pyion
import threading
import os #using this to get the file

counter = 0 #used to keep track of files in the queue
queue = [] #holds files
queueLock = threading.Lock()#avoid threads crashing
sendThread = None #keep track of background thread
entity = None #cfpd entity returned by cfpd_open(), used for transfering
proxy = None
bpProxy = None
endPoint = None #destination
statusChange = None #stores callback func to know when the status changes
activeId = None #Id of the file being sent
activeLock = threading.Lock()  #used so active_id doesn't crash

#Increments counter by 1 for everyy new file added to the queue
def nextId():
    global counter
    counter += 1
    return str(counter)

#This sets up the connection between nodes
def fileQueue(nodeNumber:int, entityId:int, bpEndpoint:str):
    global proxy, bpProxy, endpoint, entity
    proxy = pyion.get_cfdp_proxy(nodeNumber)
    bpProxy = pyion.get_bp_proxy(nodeNumber)
    endpoint = bpProxy.bp_open(bpEndpoint)
    entity = proxy.cfdp_open(entityId, endpoint)

#takes the file path and adds it to the queue as a dictionary
def queueFile(filePath):
    ids = []
    with queueLock:
        for path in filePath:
            queueId = nextId()
            queue.append({
                "id": queueId,
                "path": path,
                "fileName": os.path.basename(path),
                "size": os.path.getsize(path) if os.path.exists(path) else 0,
                "status": "Queued",
                })
            ids.append(queueId)
    return ids 

# uses the queueId to remove a file from the queue before its sent
def removeFile(queueId):
    with queueLock:
        for i, item in enumerate(queue):
            if item["id"] == queueId:
                if item["status"] == "Running":
                    return False
                queue.pop(i)
                return True
    return False

#clears the queue based on the status of each file
def clearQueue():
    with queueLock:
        removable = {"Queued", "Failed", "Canceled"}
        queue[:] = [item for item in queue if item["status"] not in removable]

#copys the queue
def getQueue():
    with queueLock:
        return [item.copy() for item in queue]

#uses background thread to send the files. Stores 'onChange' so we can get status updates. also checks for other threads.
def sendFiles(onChange):
    global sendThread, statusChange
    if sendThread and sendThread.is_alive():
        return
    statusChange = onChange
    sendThread = threading.Thread(target=processQueue, daemon=True)
    sendThread.start()

#suspend doesnt work because the files send too fast
def suspend():
    if entity:
        return entity.cfdp_suspend()
    return 0
#
def cancel():
    if entity:
        return entity.cfdp_cancel()
    return 0
#doesnt work yet
def resume():
    if entity:
        return entity.cfdp_resume()
    return 0
#returns the current transfer status as a string. It looks for the active file to get the file status
def statusIndicator():
    with activeLock:
        if activeId is None:
            return 'idle'
    with queueLock:
        item = getItemById(activeId)
        if item:
            return item["status"]
    return 'idle'

##################

#searches queue for a specific item in the queue by its ID. If we find it it seturns the dictionary for that ID. 'updateStatus' and statusIndicator' use this
def getItemById(queueId):
    for item in queue:
        if item["id"] == queueId:
            return item
    return None

#updates the file status in the queue and chages the 'statusChange'  variable
def updateStatus(queueId, status):
    with queueLock:
        item = getItemById(queueId)
        if item:
            item["status"] = status
    if statusChange:
        statusChange(queueId, status)

#cfpd event handler thasts connected to a 'queueId'
def makeEvent(queueId):
    def handler(event):
        eventName = str(event)
        if "FINISHED" in eventName:
            if hasattr(event, 'condition_code') and event.condition_code != 0:
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

#this is used for the send thread. It loops through queue looking for the next file added to the queue. If it finds one it will change the status to 'Running' and register the event handler and it will call 'cfdp_send'. This will keep going until the queue is empty.
def processQueue():
    global activeId

    while True:
        with queueLock:
            nextItem = next(
                (item.copy() for item in queue if item["status"] == "Queued"),
                None
            )

        if nextItem is None:
            break

        queueId = nextItem["id"]
        path = nextItem["path"]
        filename = nextItem["fileName"]

        with activeLock:
            activeId = queueId
        updateStatus(queueId, "Running")

        try:
            entity.register_event_handler('CFDP_ALL_EVENTS', makeEvent(queueId))
            entity.cfdp_send(source_file=path, dest_file=f'/SZ_received_files/{filename}')
            success = entity.wait_for_transaction_end()

            if not success:
                updateStatus(queueId, "Failed")

        except Exception as e:
            print(f"Couldn't send {filename}: {e}")
            updateStatus(queueId, "Failed")

        with activeLock:
            activeId = None
