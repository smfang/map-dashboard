import React, { useState } from "react";
import { Button, Form, Card, Row, Col } from "react-bootstrap";
import { ethers } from "ethers";

const NATURE_INDEX_TRACKER_ABI = [
  {
    inputs: [],
    name: "getCurrentState",
    outputs: [
      { internalType: "uint256", name: "geoIndexValue", type: "uint256" },
      { internalType: "uint256", name: "natureUnitPrice", type: "uint256" },
      { internalType: "uint256", name: "computedValue", type: "uint256" },
      {
        internalType: "uint256",
        name: "natureUnitsEquivalent",
        type: "uint256",
      },
      { internalType: "uint256", name: "lastSnapshotId", type: "uint256" },
    ],
    stateMutability: "view",
    type: "function",
  },
  {
    inputs: [],
    name: "createSnapshot",
    outputs: [{ internalType: "uint256", name: "snapshotId", type: "uint256" }],
    stateMutability: "nonpayable",
    type: "function",
  },
  {
    inputs: [{ internalType: "uint256", name: "snapshotId", type: "uint256" }],
    name: "getSnapshot",
    outputs: [
      {
        components: [
          { internalType: "uint256", name: "timestamp", type: "uint256" },
          { internalType: "uint256", name: "geoIndexValue", type: "uint256" },
          { internalType: "uint256", name: "natureUnitPrice", type: "uint256" },
          { internalType: "uint256", name: "computedValue", type: "uint256" },
        ],
        internalType: "struct NatureIndexTracker.IndexSnapshot",
        name: "",
        type: "tuple",
      },
    ],
    stateMutability: "view",
    type: "function",
  },
  {
    inputs: [],
    name: "getLatestSnapshot",
    outputs: [
      {
        components: [
          { internalType: "uint256", name: "timestamp", type: "uint256" },
          { internalType: "uint256", name: "geoIndexValue", type: "uint256" },
          { internalType: "uint256", name: "natureUnitPrice", type: "uint256" },
          { internalType: "uint256", name: "computedValue", type: "uint256" },
        ],
        internalType: "struct NatureIndexTracker.IndexSnapshot",
        name: "",
        type: "tuple",
      },
    ],
    stateMutability: "view",
    type: "function",
  },
];

export default function NatureIndexTracker({ signer, onSuccess, onError }) {
  const [trackerAddress, setTrackerAddress] = useState("");
  const [currentState, setCurrentState] = useState(null);
  const [snapshotId, setSnapshotId] = useState("");
  const [snapshot, setSnapshot] = useState(null);

  const getContract = () => {
    if (!signer || !trackerAddress)
      throw new Error("Missing signer or tracker address");
    return new ethers.Contract(
      trackerAddress,
      NATURE_INDEX_TRACKER_ABI,
      signer
    );
  };

  const handleGetCurrentState = async () => {
    try {
      const c = getContract();
      const state = await c.getCurrentState();
      setCurrentState({
        geoIndexValue: state.geoIndexValue.toString(),
        natureUnitPrice: state.natureUnitPrice.toString(),
        computedValue: state.computedValue.toString(),
        natureUnitsEquivalent: state.natureUnitsEquivalent.toString(),
        lastSnapshotId: state.lastSnapshotId.toString(),
      });
    } catch (e) {
      onError?.(e.message);
    }
  };

  const handleCreateSnapshot = async () => {
    try {
      const c = getContract();
      const tx = await c.createSnapshot();
      await tx.wait();
      onSuccess?.("Snapshot created successfully");
      handleGetCurrentState(); // Refresh state
    } catch (e) {
      onError?.(e.message);
    }
  };

  const handleGetSnapshot = async () => {
    try {
      const c = getContract();
      const snapshotData = await c.getSnapshot(snapshotId);
      setSnapshot({
        timestamp: snapshotData.timestamp.toString(),
        geoIndexValue: snapshotData.geoIndexValue.toString(),
        natureUnitPrice: snapshotData.natureUnitPrice.toString(),
        computedValue: snapshotData.computedValue.toString(),
      });
    } catch (e) {
      onError?.(e.message);
    }
  };

  const formatValue = (value, decimals = 18) => {
    return (Number(value) / Math.pow(10, decimals)).toFixed(6);
  };

  return (
    <Card>
      <Card.Body>
        <Card.Title>Nature Index Tracker</Card.Title>
        <Form>
          <Form.Group className="mb-3">
            <Form.Label>Tracker Address</Form.Label>
            <Form.Control
              placeholder="0x..."
              value={trackerAddress}
              onChange={(e) => setTrackerAddress(e.target.value)}
            />
          </Form.Group>

          <div className="d-flex gap-2 mb-3">
            <Button variant="primary" onClick={handleGetCurrentState}>
              Get Current State
            </Button>
            <Button variant="success" onClick={handleCreateSnapshot}>
              Create Snapshot
            </Button>
          </div>

          {currentState && (
            <Card className="mt-3">
              <Card.Header>Current State</Card.Header>
              <Card.Body>
                <Row>
                  <Col md={6}>
                    <div>
                      <strong>Geo Index Value:</strong>{" "}
                      {formatValue(currentState.geoIndexValue)}
                    </div>
                    <div>
                      <strong>Nature Unit Price:</strong> $
                      {formatValue(currentState.natureUnitPrice)}
                    </div>
                    <div>
                      <strong>Computed Value:</strong> $
                      {formatValue(currentState.computedValue)}
                    </div>
                  </Col>
                  <Col md={6}>
                    <div>
                      <strong>Nature Units Equivalent:</strong>{" "}
                      {formatValue(currentState.natureUnitsEquivalent)}
                    </div>
                    <div>
                      <strong>Last Snapshot ID:</strong>{" "}
                      {currentState.lastSnapshotId}
                    </div>
                  </Col>
                </Row>
              </Card.Body>
            </Card>
          )}

          <Form.Group className="mb-3">
            <Form.Label>Snapshot ID</Form.Label>
            <Form.Control
              placeholder="0"
              value={snapshotId}
              onChange={(e) => setSnapshotId(e.target.value)}
            />
          </Form.Group>

          <Button variant="info" onClick={handleGetSnapshot}>
            Get Snapshot
          </Button>

          {snapshot && (
            <Card className="mt-3">
              <Card.Header>Snapshot Data</Card.Header>
              <Card.Body>
                <div>
                  <strong>Timestamp:</strong>{" "}
                  {new Date(Number(snapshot.timestamp) * 1000).toLocaleString()}
                </div>
                <div>
                  <strong>Geo Index Value:</strong>{" "}
                  {formatValue(snapshot.geoIndexValue)}
                </div>
                <div>
                  <strong>Nature Unit Price:</strong> $
                  {formatValue(snapshot.natureUnitPrice)}
                </div>
                <div>
                  <strong>Computed Value:</strong> $
                  {formatValue(snapshot.computedValue)}
                </div>
              </Card.Body>
            </Card>
          )}
        </Form>
      </Card.Body>
    </Card>
  );
}

