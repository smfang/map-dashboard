import React, { useState } from "react";
import { Button, Form, Card } from "react-bootstrap";
import { ethers } from "ethers";

const ERC20_ABI = [
  {
    inputs: [],
    name: "totalSupply",
    outputs: [{ internalType: "uint256", name: "", type: "uint256" }],
    stateMutability: "view",
    type: "function",
  },
  {
    inputs: [],
    name: "decimals",
    outputs: [{ internalType: "uint8", name: "", type: "uint8" }],
    stateMutability: "view",
    type: "function",
  },
  {
    inputs: [],
    name: "name",
    outputs: [{ internalType: "string", name: "", type: "string" }],
    stateMutability: "view",
    type: "function",
  },
  {
    inputs: [],
    name: "symbol",
    outputs: [{ internalType: "string", name: "", type: "string" }],
    stateMutability: "view",
    type: "function",
  },
];

export default function GeoIndexTokenView({ signer, onError }) {
  const [address, setAddress] = useState("");
  const [info, setInfo] = useState(null);

  const handleRead = async () => {
    try {
      if (!signer || !address)
        throw new Error("Missing signer or token address");
      const c = new ethers.Contract(address, ERC20_ABI, signer);
      const [name, symbol, decimals, supply] = await Promise.all([
        c.name(),
        c.symbol(),
        c.decimals(),
        c.totalSupply(),
      ]);
      const supplyStr = supply.toString();
      const human = Number(ethers.utils.formatUnits(supply, decimals));
      setInfo({ name, symbol, decimals, supply: supplyStr, indexValue: human });
    } catch (e) {
      onError?.(e.message);
    }
  };

  return (
    <Card>
      <Card.Body>
        <Card.Title>Geo Index Token</Card.Title>
        <Form>
          <Form.Group className="mb-3">
            <Form.Label>Token Address</Form.Label>
            <Form.Control
              placeholder="0x..."
              value={address}
              onChange={(e) => setAddress(e.target.value)}
            />
          </Form.Group>
          <Button onClick={handleRead}>Read Index</Button>
        </Form>
        {info && (
          <div className="mt-3">
            <div>
              Name: {info.name} ({info.symbol})
            </div>
            <div>Decimals: {info.decimals}</div>
            <div>Total Supply (raw): {info.supply}</div>
            <div>Mirrored Index (1e18 scale): {info.indexValue.toFixed(6)}</div>
          </div>
        )}
      </Card.Body>
    </Card>
  );
}
