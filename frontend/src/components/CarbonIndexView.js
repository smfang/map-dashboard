import React, { useState } from "react";
import { Button, Form, Card } from "react-bootstrap";
import { ethers } from "ethers";

const CARBON_INDEX_ABI = [
  {
    inputs: [],
    name: "getIndex",
    outputs: [{ internalType: "uint256", name: "", type: "uint256" }],
    stateMutability: "view",
    type: "function",
  },
];

export default function CarbonIndexView({ signer, onError }) {
  const [address, setAddress] = useState("");
  const [value, setValue] = useState(null);

  const handleRead = async () => {
    try {
      if (!signer || !address) throw new Error("Missing signer or address");
      const c = new ethers.Contract(address, CARBON_INDEX_ABI, signer);
      const v = await c.getIndex();
      setValue(v);
    } catch (e) {
      onError?.(e.message);
    }
  };

  return (
    <Card>
      <Card.Body>
        <Card.Title>Carbon Index</Card.Title>
        <Form>
          <Form.Group className="mb-3">
            <Form.Label>Contract Address</Form.Label>
            <Form.Control
              placeholder="0x..."
              value={address}
              onChange={(e) => setAddress(e.target.value)}
            />
          </Form.Group>
          <Button onClick={handleRead}>Read Index</Button>
        </Form>
        {value !== null && (
          <div className="mt-3">
            <div>Raw: {value.toString()}</div>
            <div>Scaled: {(Number(value.toString()) / 1e18).toFixed(6)}</div>
          </div>
        )}
      </Card.Body>
    </Card>
  );
}


