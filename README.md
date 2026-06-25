# CSP RP-01 Format Specifications

**Transmission Method**
- Transport: TCP (Continuous Line-Based Stream)

Panel sends handshake to the receiver, receiver responds with receiver ID number which is 4 digits, which the panel can verify with the programmed value, which helps prevents MITM attacks. Panel sends payload/events using a **Three-Step Echo Verification Sequence**.

All communication occurs over a continuous TCP stream. When a client connects to the receiver on the specified port (By default it is 9000, but recommended to be changed), it must initiate a handshake before transmitting event data. Every transmission from both client and receiver must terminate with a newline (`\n`) character.

- Step 1 (Handshake): The client connects and transmits an initial handshake string, for added secerity, the receiver can be implemented to only accept specific handshakes, which can help reduce spam.
- Step 2 (Receiver Validation): The receiver reads the data. If no data arrives, the connection is terminated immediately.
- Step 3 (Receiver Identification): Upon receiving a valid handshake, the receiver replies with its 4-character Identification Token followed by a newline character (`AAAA\n`). You may implement a validation process, where the client verifies this with a predefined receiver ID programmed in the panel, and if not valid, the client could choose to terminate the connection.

---

## Data Integrity Validation
To prevent data corruption and ensure packet integrity over network pathways, the protocol uses a **Stop-and-Wait Echo Verification** loop for every individual event frame before any logic is processed:

1. **Step 1 (Panel Transmission):** The panel sends its standard fixed-width event message line across the TCP stream.
2. **Step 2 (Receiver Echo Response):** The receiver reads the line. If it meets the minimum length, the receiver prepends an `ACK ` flag directly to the *payload* it just received, followed by a newline:
   `ACK [payload]\n`
3. **Step 3 (Panel Final ACK):** The panel compares this echo response against its internal transmission buffer. If it matches perfectly, the panel replies with a standalone confirmation token line: `ACK\n`.
   - *Success:* Upon receiving this final `ACK\n`, the receiver commits the event and executes secondary logic (such as Expanded Data or Watch Mode).
   - *Failure/Timeout:* If the echo does not match or the final `ACK\n` never arrives, the receiver flags a validation error, discards the frame, and the panel must re-transmit the original event.

---

## Event Sending Format
Every standard packet must be at least 25 characters long, with the ABSOLUTE MAX of 29 characters.
`AAAAAAAAAA ET Q EEE GG CCC SSSS`

- **A** = Account Number (10 characters, indices 0-9)
- **ET** = Event Type (6 characters, indices 10-15)
- **Q** = Qualifier (1 character, index 16)
- **EEE** = Event code (3 characters, indices 17-19)
- **GG** = Partition (2 characters, indices 20-21)
- **CCC** = Zone (3 characters, indices 22-24)
- **SSSS** = More notes / Parameters (4 characters, indices 25-28)

*Note: If the panel sends less than 25 characters, the receiver will log an E02 data error and ignore the data sent.*

---

### *ET options*
- **01) New Event**
- **02) Expanded Data**
  When the 6-character Event Type (et) field ends in `02`, it signals that the standard fixed fields are followed by an unformatted descriptive text stream.
- **03) Watch Mode**
  When the Event Type (et) ends in `03` and the Event Code (eee) matches exactly `F92`, the system enters a monitoring window designed to catch panel tampering or line cuts.
- **04) Future use**

### *Qualifier Options*
- `1` = New event / Opening.
- `3` = Restore / Closing.
- `6` = Status (still present).

### *More Notes options:*
- `1` = More events coming
- `2` = All done (End connection)

---

## Special Operations

### Watch Mode Execution
If event type is watch mode (ends in `03`), and the event code is `F92`, the receiver will parse the 4-character status field (`ssss`) as an integer representing a countdown timer in seconds. 
- The receiver yields control and asynchronously blocks, waiting for any subsequent network frame from the client within that exact duration.
- **Timeout Exception:** If the countdown timer lapses without further client activity, the receiver raises a high-priority alert: `WATCH MODE TIMEOUT. Alerting Smash and Crash` and logs an internal **Event 777**.
- Watch mode events are usually sent during an entry/exit delay.

### Expanded Data Processing
If the ET is Expanded data (ends in `02`), it will then expect a raw text input stream on the subsequent line. The receiver reads this text input directly from the buffer and logs it.

---

## Standardised Error Codes
- **E01:** Connection Error: The connection was dropped before the receiver could complete the handshake.
- **E02:** Data Error: The panel sent invalid or short data (less than 25 characters).
- **E03:** Unknown Error
- **E04:** General Exception: System or processing crash handler.
- **E502:** Connection Reset: Connection abruptly reset by the client host.

## Session Teardown
Connections can be gracefully closed by the client from within the payload stream. If the status field (`ssss`) starts with the character `2` (representing "All done"), the receiver logs an End of Transmission request, terminates the message processing loop, and safely tears down the underlying TCP connection.

## Development
We highly encourage you implement CSP RC-01 in your own projects! If you need assistance, open a issue. If you have ideas, open a PR.

**AI USE**
Artificial Intelligence was used in assisting making the readme, with fixing typos and gramatical errors. AI was also used for making test.py, and int rying many different scenarios.