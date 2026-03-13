import pyion

# Favorites list. Not tested yet
class Contact:
    def __init__(self, contact_id, name, peer_entity_num, favorite=False,
                 last_contacted=None, default_remote_dir=None, notes=None):
        self.id = contact_id
        self.name = name
        self.peer_entity_num = peer_entity_num
        self.favorite = favorite
        self.last_contacted = last_contacted
        self.default_remote_dir = default_remote_dir
        self.notes = notes

    def rename(self, name):
        self.name = name

    def set_favorite(self, favorite):
        self.favorite = bool(favorite)

    def last_contact(self, when):
        self.last_contacted = when

    def set_default_remote_dir(self, remote_dir):
        self.default_remote_dir = remote_dir

    def set_notes(self, notes):
        self.notes = notes

# PYION wrapper. 
class session:
    def __init__(self, local_node, local_eid, peer_entity):
        self.local_node = local_node
        self.local_eid = local_eid
        self.peer_entity_nbr = peer_entity

        self.bpxy = None
        self.cpxy = None
        self.endpoint = None
        self.entity = None
    
    def set_peer(self):
        # TODO: rn, session will only have one entity and endpoint. Perhaps we
        # use another module as a controller so we can have multiple sessions
        # or disconnect/reconnect to change peer node
        pass
    
    def connect(self):
        if self.entity is not None:
            # already connected
            return

        # get proxies
        self.bpxy = pyion.get_bp_proxy(self.local_node)
        self.cpxy = pyion.get_cfdp_proxy(self.local_node)

        # open endpoints
        self.endpoint = self.bpxy.bp_open(self.local_eid)
        self.entity = self.cpxy.cfdp_open(self.peer_entity_nbr, self.endpoint)
		
    def disconnect(self):
        # closing proxies and resetting variables
        self.cpxy.cfdp_close(self.peer_entity_nbr)
        self.bpxy.bp_close(self.endpoint)

        self.endpoint = None
        self.entity = None
		
    # Everything else here is just forwardding our function calls
    def send(self, source_file, dest_file=None, mode=None,
                    closure_lat=None, seg_metadata=None):
        if dest_file is None:
            dest_file = source_file
        self.entity.cfdp_send(source_file, dest_file, mode,
                            closure_lat, seg_metadata)
        
    def request(self, source_file, dest_file=None, mode=None,
				  	 closure_lat=None, seg_metadata=None):
        if dest_file is None:
            dest_file = source_file
        self.entity.cfdp_request(source_file, dest_file, mode,
                            closure_lat, seg_metadata)
		
    def cancel(self):
        self.entity.cfdp_cancel()
	
    def suspend(self):
        self.entity.cfdp_suspend()

	
    def resume(self):
        self.entity.cfdp_resume()

	
    def report(self):
        self.entity.cfdp_report()

    def add_usr_message(self, msg):
        self.entity.add_usr_message(msg)

    def add_filestore_request(self, action, file1, file2=None):
        self.entity.add_filestore_request(action, file1, file2)
	
    def ev_handler(self, event, func):
        self.entity.register_event_handler(event, func)

    def wait_for_tx(self, timeout=None):
        self.entity.wait_for_transaction_end(timeout)
    