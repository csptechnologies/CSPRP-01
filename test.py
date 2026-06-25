## Artificial intelligence was used when generating this
import asyncio
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s'
)

HOST = '127.0.0.1'
PORT = 9000

async def send_and_verify(reader, writer, payload: str):
    """
    Helper function that handles the 3-step loopback protocol:
    1. Sends the event payload
    2. Reads the receiver's echo response and checks for 'ACK [payload]'
    3. Sends back a final 'ACK' line if correct
    """
    logging.info(f"Step 1: Sending payload -> {payload}")
    writer.write((payload + "\n").encode())
    await writer.drain()

    # Step 2: Read echo from receiver
    echo_data = await reader.readline()
    if not echo_data:
        logging.error("Receiver disconnected during echo phase.")
        return False

    echo_response = echo_data.decode().strip()
    logging.info(f"Step 2: Received echo -> {echo_response}")

    expected_echo = f"ACK {payload}"
    if echo_response == expected_echo:
        # Step 3: Send final ACK confirmation line
        logging.info("Step 3: Echo matches perfectly! Sending final ACK.")
        writer.write("ACK\n".encode())
        await writer.drain()
        return True
    else:
        logging.error(f"Echo mismatch! Expected '{expected_echo}', got '{echo_response}'")
        return False

async def run_test_panel():
    logging.info(f"Connecting to receiver at {HOST}:{PORT}...")
    try:
        reader, writer = await asyncio.open_connection(HOST, PORT)
    except ConnectionRefusedError:
        logging.error("Could not connect to the receiver. Is it running?")
        return

    try:
        # --- PHASE 1: HANDSHAKE ---
        logging.info("Initiating Handshake...")
        writer.write("HELLO\n".encode())
        await writer.drain()

        receiver_id_data = await reader.readline()
        receiver_id = receiver_id_data.decode().strip()
        logging.info(f"Handshake Complete. Receiver ID: {receiver_id}")
        
        await asyncio.sleep(1)  # Brief pause between steps for clear log reading

        # --- PHASE 2: STANDARD EVENT TEST ---
        # acct=9999999999, et=000001, q=1, eee=130, gg=01, ccc=005, ssss=0001
        standard_payload = "99999999990000011130010050001"
        success = await send_and_verify(reader, writer, standard_payload)
        
        await asyncio.sleep(2)

        # --- PHASE 3: EXPANDED DATA MODE TEST ---
        # et ends in '02' triggers expanded text parsing
        # acct=9999999999, et=000002, q=1, eee=000, gg=00, ccc=000, ssss=0001
        expanded_trigger = "99999999990000021000000000001"
        if await send_and_verify(reader, writer, expanded_trigger):
            logging.info("Sending supplementary expanded text data line...")
            writer.write("ZONE 05 BYPASSED - FRONT DOOR\n".encode())
            await writer.drain()

        await asyncio.sleep(2)

        # --- PHASE 4: WATCH MODE (SMASH & CRASH) TEST ---
        # et ends in '03' and eee='F92' sets a timer using ssss ('0004' = 4 seconds)
        # acct=9999999999, et=000003, q=1, eee=F92, gg=00, ccc=000, ssss=0004
        watch_payload = "99999999990000031F92000000004"
        if await send_and_verify(reader, writer, watch_payload):
            logging.info("Watch Mode active on receiver. Waiting 2 seconds before sending checking signal...")
            await asyncio.sleep(2)
            
            logging.info("Sending check-in signal within the watch window...")
            writer.write("PANEL_OK\n".encode())
            await writer.drain()

        await asyncio.sleep(2)

        # --- PHASE 5: SHUTDOWN SIGNAL TEST ---
        # ssss starts with '2' requests end of transmission
        # acct=9999999999, et=000001, q=1, eee=000, gg=00, ccc=000, ssss=2000
        shutdown_payload = "99999999990000011000000002000"
        await send_and_verify(reader, writer, shutdown_payload)

    except Exception as e:
        logging.error(f"Test Exception encountered: {e}")
    finally:
        logging.info("Closing test connection.")
        writer.close()
        await writer.wait_closed()

if __name__ == '__main__':
    try:
        asyncio.run(run_test_panel())
    except KeyboardInterrupt:
        logging.info("Test panel interrupted.")