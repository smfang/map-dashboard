import React, { useState } from "react";
import { Button, Form, Card, Row, Col } from "react-bootstrap";
import { ethers } from "ethers";

const UMA_ORACLE_ABI = [
  {
    inputs: [
      { internalType: "bytes32", name: "dataId", type: "bytes32" },
      { internalType: "bytes32", name: "data", type: "bytes32" },
      { internalType: "address", name: "asserter", type: "address" },
    ],
    name: "assertDataFor",
    outputs: [
      { internalType: "bytes32", name: "assertionId", type: "bytes32" },
    ],
    stateMutability: "nonpayable",
    type: "function",
  },
  {
    inputs: [{ internalType: "bytes32", name: "assertionId", type: "bytes32" }],
    name: "settle",
    outputs: [
      { internalType: "bool", name: "assertedTruthfully", type: "bool" },
    ],
    stateMutability: "nonpayable",
    type: "function",
  },
  {
    inputs: [{ internalType: "bytes32", name: "dataId", type: "bytes32" }],
    name: "latest",
    outputs: [
      { internalType: "bool", name: "isResolved", type: "bool" },
      { internalType: "bool", name: "truthfully", type: "bool" },
      { internalType: "bytes32", name: "data", type: "bytes32" },
      { internalType: "bytes32", name: "assertionId", type: "bytes32" },
    ],
    stateMutability: "view",
    type: "function",
  },
  {
    inputs: [{ internalType: "bytes32", name: "dataId", type: "bytes32" }],
    name: "latestResolved",
    outputs: [{ internalType: "bytes32", name: "", type: "bytes32" }],
    stateMutability: "view",
    type: "function",
  },
];

export default function UMAOracle({ signer, onSuccess, onError }) {
  const [oracleAddress, setOracleAddress] = useState("");
  const [dataIdHex, setDataIdHex] = useState("");
  const [dataHex, setDataHex] = useState("");
  const [assertionIdHex, setAssertionIdHex] = useState("");
  const [latestInfo, setLatestInfo] = useState(null);

  const getContract = () => {
    if (!signer || !oracleAddress)
      throw new Error("Missing signer or oracle address");
    return new ethers.Contract(oracleAddress, UMA_ORACLE_ABI, signer);
  };

  const handleAssert = async () => {
    try {
      const c = getContract();
      const tx = await c.assertDataFor(
        dataIdHex,
        dataHex,
        await signer.getAddress()
      );
      const receipt = await tx.wait();
      const event = receipt.logs?.[0];
      onSuccess?.("Assertion submitted");
    } catch (e) {
      onError?.(e.message);
    }
  };

  const handleSettle = async () => {
    try {
      const c = getContract();
      const tx = await c.settle(assertionIdHex);
      await tx.wait();
      onSuccess?.("Assertion settled");
    } catch (e) {
      onError?.(e.message);
    }
  };

  const handleLatest = async () => {
    try {
      const c = getContract();
      const res = await c.latest(dataIdHex);
      setLatestInfo({
        isResolved: res.isResolved,
        truthfully: res.truthfully,
        data: res.data,
        assertionId: res.assertionId,
      });
    } catch (e) {
      onError?.(e.message);
    }
  };

  const handleLatestResolved = async () => {
    try {
      const c = getContract();
      const res = await c.latestResolved(dataIdHex);
      setLatestInfo({ resolvedData: res });
    } catch (e) {
      onError?.(e.message);
    }
  };

  return (
    <Card>
      <Card.Body>
        <Card.Title>UMA Input Oracle</Card.Title>
        <Form>
          <Form.Group className="mb-3">
            <Form.Label>Oracle Address</Form.Label>
            <Form.Control
              placeholder="0x..."
              value={oracleAddress}
              onChange={(e) => setOracleAddress(e.target.value)}
            />
          </Form.Group>

          <Row>
            <Col md={6}>
              <Form.Group className="mb-3">
                <Form.Label>Data ID (bytes32 hex)</Form.Label>
                <Form.Control
                  placeholder="0x..."
                  value={dataIdHex}
                  onChange={(e) => setDataIdHex(e.target.value)}
                />
              </Form.Group>
            </Col>
            <Col md={6}>
              <Form.Group className="mb-3">
                <Form.Label>Data (bytes32 hex)</Form.Label>
                <Form.Control
                  placeholder="0x..."
                  value={dataHex}
                  onChange={(e) => setDataHex(e.target.value)}
                />
              </Form.Group>
            </Col>
          </Row>

          <div className="d-flex gap-2 mb-3">
            <Button variant="primary" onClick={handleAssert}>
              Assert
            </Button>
            <Button variant="secondary" onClick={handleLatest}>
              Latest
            </Button>
            <Button variant="secondary" onClick={handleLatestResolved}>
              Latest Resolved
            </Button>
          </div>

          <Form.Group className="mb-3">
            <Form.Label>Assertion ID (bytes32 hex)</Form.Label>
            <Form.Control
              placeholder="0x..."
              value={assertionIdHex}
              onChange={(e) => setAssertionIdHex(e.target.value)}
            />
          </Form.Group>

          <Button variant="warning" onClick={handleSettle}>
            Settle
          </Button>
        </Form>

        {latestInfo && (
          <Card className="mt-3">
            <Card.Body>
              <pre style={{ whiteSpace: "pre-wrap" }}>
                {JSON.stringify(latestInfo, null, 2)}
              </pre>
            </Card.Body>
          </Card>
        )}
      </Card.Body>
    </Card>
  );
}


