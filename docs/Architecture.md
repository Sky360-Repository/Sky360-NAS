# s360-nas-node Architecture
Sky360 Project - NAS Node Specification

## 1. Overview

`s360-nas-node` is the **central data archival node** in the Sky360 system.
Its purpose is to:

- Receive data streams from **all Sky360 nodes** (CORE, ASC, PTF, RADAR)
- Use **CAN bus** for low-latency, low-overhead inter-node transport
- Store incoming data on a **Network Attached Storage (NAS)**
- Organize data by **node**, **date**, **type**, and **timestamp**
- Provide **archival integrity**, **redundancy**, and **long-term storage**
- Publish storage status and health over **eCAL**


## 2. High-Level Architecture

```
s360-nas-node
 +-- orchestrator/
 |     +-- main orchestrator loop
 |     +-- module lifecycle mgmt
 |     +-- eCAL publishers/subscribers
 |     +-- CAN bus routing
 |
 +-- canbus/
 |     +-- CAN receiver (multi-node)
 |     +-- CAN frame parser
 |     +-- pb.sky.NasRecord (internal)
 |
 +-- writer/
 |     +-- NAS filesystem writer
 |     +-- directory structure manager
 |     +-- compression (optional)
 |     +-- pb.sky.NasWriteStatus publisher
 |
 +-- housekeeping/
       +-- disk usage monitor
       +-- retention policy
       +-- pb.sky.NasNodeStatus publisher
```

## 3. Component Responsibilities

### **Orchestrator**
- Starts/stops modules
- Routes CAN frames - NAS writer
- Publishes heartbeat/status
- Manages eCAL publishers/subscribers
- Ensures deterministic ingestion timing
- Handles backpressure (queue limits, frame dropping)

### **CAN Bus Module**
- Receives CAN frames from all nodes
- Decodes node ID, message type, payload
- Converts CAN frames into internal `NasRecord` objects
- Handles multi-node arbitration
- Provides timestamps for NAS storage

### **NAS Writer Module**
- Writes records to NAS filesystem
- Organizes data by date/node/type
- Ensures atomic writes
- Supports optional compression (lz4/zstd)
- Publishes `NasWriteStatus`

### **Housekeeping Module**
- Monitors disk usage
- Enforces retention policies (delete old data)
- Publishes `NasNodeStatus`
- Ensures NAS health and availability

# 4. Interfaces

Below are the formal interface definitions for **data flow**, **processing stages**, **inputs**, **outputs**, and **eCAL topics**.

## 4.1 DATA FLOW & ARCHITECTURE

| Component | Direction | Data Type | Topic | Description |
|----------|-----------|-----------|--------|-------------|
| CAN Bus Module | In | CAN frame | `CAN bus` | Data from CORE/ASC/PTF/RADAR |
| CAN Bus Module | Out | `NasRecord` | internal | Parsed CAN payload |
| NAS Writer | Out | `NasWriteStatus` | `sky360/nas/write_status` | Write success/failure |
| Housekeeping | Out | `NasNodeStatus` | `sky360/nas/status` | Disk usage + health |
| Orchestrator | In | `TimingMessage` | `sky360/timing` | GNSS time alignment |

## 4.2 PROCESSING STAGES

| Stage | Process | Input | Output | Configurable | Notes |
|-------|---------|--------|---------|--------------|-------|
| CAN Acquisition | Receive CAN frames | CAN bus | Raw frame | Baud rate | Multi-node |
| CAN Decode | Parse frame | Raw frame | NasRecord | Node map | Lightweight |
| NAS Write | Write to NAS | NasRecord | File | Compression | Atomic writes |
| Housekeeping | Disk mgmt | Filesystem | Status | Retention | Prevents overflow |

## 4.3 INPUT FIELDS (CAN - NAS)

### **NasRecord Input Fields**

| Field Name | Type | Required | Description |
|------------|------|----------|-------------|
| node | string | Yes | Source node (core/asc/ptf/radar) |
| msg_type | string | Yes | status/event/frame/track/etc |
| payload | bytes/string | Yes | CAN payload |
| timestamp | Timestamp | Yes | GNSS or monotonic time |

## 4.4 OUTPUT FIELDS (NAS - other nodes)

### **NasWriteStatus Output**

| Field | Type | Description |
|-------|------|-------------|
| path | string | File written |
| success | bool | Write success |
| timestamp | Timestamp | Write time |

### **NasNodeStatus Output**

| Field | Type | Description |
|-------|------|-------------|
| disk_used_pct | float | Disk usage percentage |
| disk_free_gb | float | Free space |
| retention_active | bool | Whether cleanup is running |
| timestamp | Timestamp | Status time |

# 5. eCAL TOPIC DEFINITIONS

| Topic Name | Direction | Message Type | Description |
|------------|-----------|--------------|-------------|
| `sky360/nas/write_status` | Out | `NasWriteStatus` | Write success/failure |
| `sky360/nas/status` | Out | `NasNodeStatus` | Disk usage + health |
| `sky360/timing` | In | `TimingMessage` | GNSS time alignment |

# 6. Directory Structure

The NAS writer organizes data as:

```
/mnt/nas/sky360/
   YYYYMMDD/
      core/
         status_1691234567890.log
         adsb_1691234567891.log
      asc/
         frame_1691234567892.bin
         events_1691234567893.json
      ptf/
         track_1691234567894.json
      radar/
         doa_1691234567895.json
```

This ensures:

- Chronological ordering
- Node separation
- Easy retrieval
- Compatibility with offline analysis tools


