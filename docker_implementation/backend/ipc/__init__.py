"""ZeroMQ IPC layer between the host process and the in-container agent.

- ``protocol`` — request / reply / event JSON schemas and the method whitelist.
- ``server`` — REP + PUB server that runs inside the container, bound to a
  ``BackendFacade``.
- ``client`` — host-side ``IpcClient`` used by the ZmqController and the GUI.
- ``path_map`` — pure host-path <-> container-path translation.
"""
