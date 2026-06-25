import asyncio
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s'
)

RECEIVERID = "AAAA"
PORT = 9000

async def clientcontrol(reader, writer):
    addr = writer.get_extra_info('peername')
    logging.info(f"New connection from {addr}")

    try:
        handshakedata = await reader.readline()
        if not handshakedata:
            logging.warning(f"Connection error, E01 {addr}")
            writer.close()
            await writer.wait_closed()
            return
        
        logging.info(f"Handshake received from {addr}: {handshakedata.decode().strip()}")

        writer.write((RECEIVERID + "\n").encode())
        await writer.drain()
        logging.info(f"Receiver Identification was sent to {addr}")
        while True:
            data = await reader.readline()
            if not data:
                break

            payload = data.decode().strip()

            if len(payload) < 25:
                logging.warning(f"Connection error, E02 {addr}")
                continue

            acct = payload[0:10]
            et   = payload[10:16]
            q    = payload[16:17]
            eee  = payload[17:20]
            gg   = payload[20:22]
            ccc  = payload[22:25]
            ssss = payload[25:29]

            logging.info(f"Received data from {addr}: acct={acct}, et={et}, q={q}, eee={eee}, gg={gg}, ccc={ccc}, ssss={ssss}")
            echo_response = f"ACK {payload}\n"
            writer.write(echo_response.encode())
            await writer.drain()
            logging.info(f"Echo verification sent to {addr}. Awaiting final ACK...")
            confirmation_data = await reader.readline()
            if not confirmation_data:
                logging.warning(f"Connection dropped by {addr} during echo verification.")
                break
            panel_ack = confirmation_data.decode().strip()
            if panel_ack != "ACK":
                logging.warning(f"Validation failed. Panel sent '{panel_ack}' instead of ACK. Dropping frame.")
                continue
            logging.info(f"Data Integrity Validated for {acct}")            
            if et.endswith("02") or et == "02":
                logging.info(f"{acct} will be sending expanded data.")
                expandedtext = await reader.readline()
                if expandedtext:
                    logging.info(f"Expanded data received from {addr}: {expandedtext.decode().strip()}")
                continue

            if (et.endswith("03") or et == "03") and eee == "F92":
                try:
                    wmtimer = int(ssss)
                    logging.info(f"Acct {acct}: Watch mode: Waiting {wmtimer} seconds...")
                    nextevent = await asyncio.wait_for(reader.readline(), timeout=wmtimer)
                    if nextevent:
                        logging.info(f"Acct {acct}: Event Received during Watch Mode -> {nextevent.decode().strip()}")
                except ValueError:
                    logging.error(f"Acct {acct}: Invalid watch mode timer value: {ssss}")
                except asyncio.TimeoutError:
                    logging.warning(f"Acct {acct}: WATCH MODE TIMEOUT. Alerting Smash and Crash")

            if ssss.startswith("2"):
                logging.info(f"Acct {acct}: End of transmission requested ('All done'). Closing connection.")
                break
        
    except ConnectionResetError:
        logging.warning(f"E502: Connection reset by {addr}")
    except Exception as e:
        logging.error(f"E04: {e}")
    finally:
        logging.info(f"Closing Connection with {addr}\n" + "-"*40)
        writer.close()
        await writer.wait_closed()

async def main():
    server = await asyncio.start_server(clientcontrol, '0.0.0.0', PORT)
    addr = server.sockets[0].getsockname()
    print("Author: Ryan Kim")
    print("Receiver is now Up")
    async with server:
        await server.serve_forever()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Receiver shutting down.")