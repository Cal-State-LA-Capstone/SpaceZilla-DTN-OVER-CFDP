import pyion

class TestBackend:
	def __init__(self, ipn, node):
		self._ipn = "ipn:" + str(ipn)
		self._node = node
		self._proxy = pyion.get_bp_proxy(node)

	def sendMessage(self, destIPN, message):
		with self._proxy.bp_open(self._ipn) as eid:
			eid.bp_send(destIPN, message)
