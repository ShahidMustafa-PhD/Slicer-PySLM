class OPCUAAdapter:
    """Infrastructure adapter for machine communication."""
    
    def __init__(self, endpoint: str):
        self.endpoint = endpoint
        self.connected = False

    def connect(self):
        print(f"Connecting to machine at {self.endpoint}...")
        self.connected = True

    def send_process_parameters(self, power, speed):
        if not self.connected:
            raise ConnectionError("Not connected to OPC UA server")
        print(f"Setting machine Parameters: P={power}W, V={speed}mm/s")
        # Logic to write to OPC UA nodes
