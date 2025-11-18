import React, { useState } from "react";
import { Button, Form, Card, Row, Col, Alert } from "react-bootstrap";
import { ethers } from "ethers";

const REWARD_TOKEN_ABI = [
  {
    inputs: [],
    name: "getTokenInfo",
    outputs: [
      { internalType: "address", name: "_geoIndexToken", type: "address" },
      { internalType: "uint256", name: "_lastIndexValue", type: "uint256" },
      { internalType: "uint256", name: "_mintRate", type: "uint256" },
      { internalType: "uint256", name: "_maxTotalSupply", type: "uint256" },
      { internalType: "uint256", name: "_totalMinted", type: "uint256" },
      { internalType: "uint256", name: "_lastMintTimestamp", type: "uint256" },
      { internalType: "bool", name: "_mintingEnabled", type: "bool" },
    ],
    stateMutability: "view",
    type: "function",
  },
  {
    inputs: [],
    name: "getCurrentIndexValue",
    outputs: [{ internalType: "uint256", name: "", type: "uint256" }],
    stateMutability: "view",
    type: "function",
  },
  {
    inputs: [],
    name: "getPendingRewards",
    outputs: [{ internalType: "uint256", name: "", type: "uint256" }],
    stateMutability: "view",
    type: "function",
  },
  {
    inputs: [{ internalType: "address", name: "recipient", type: "address" }],
    name: "checkAndMintRewards",
    outputs: [
      { internalType: "uint256", name: "mintedAmount", type: "uint256" },
    ],
    stateMutability: "nonpayable",
    type: "function",
  },
  {
    inputs: [
      { internalType: "address[]", name: "recipients", type: "address[]" },
    ],
    name: "batchCheckAndMintRewards",
    outputs: [
      { internalType: "uint256", name: "totalMinted", type: "uint256" },
    ],
    stateMutability: "nonpayable",
    type: "function",
  },
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
    inputs: [{ internalType: "address", name: "account", type: "address" }],
    name: "balanceOf",
    outputs: [{ internalType: "uint256", name: "", type: "uint256" }],
    stateMutability: "view",
    type: "function",
  },
];

export default function RewardTokenView({ signer, onSuccess, onError }) {
  const [tokenAddress, setTokenAddress] = useState("");
  const [recipientAddress, setRecipientAddress] = useState("");
  const [tokenInfo, setTokenInfo] = useState(null);
  const [pendingRewards, setPendingRewards] = useState(null);
  const [userBalance, setUserBalance] = useState(null);

  const getContract = () => {
    if (!signer || !tokenAddress)
      throw new Error("Missing signer or token address");
    return new ethers.Contract(tokenAddress, REWARD_TOKEN_ABI, signer);
  };

  const handleGetTokenInfo = async () => {
    try {
      const c = getContract();
      const info = await c.getTokenInfo();
      setTokenInfo({
        geoIndexToken: info._geoIndexToken,
        lastIndexValue: info._lastIndexValue.toString(),
        mintRate: info._mintRate.toString(),
        maxTotalSupply: info._maxTotalSupply.toString(),
        totalMinted: info._totalMinted.toString(),
        lastMintTimestamp: info._lastMintTimestamp.toString(),
        mintingEnabled: info._mintingEnabled,
      });
    } catch (e) {
      onError?.(e.message);
    }
  };

  const handleGetPendingRewards = async () => {
    try {
      const c = getContract();
      const pending = await c.getPendingRewards();
      setPendingRewards(pending.toString());
    } catch (e) {
      onError?.(e.message);
    }
  };

  const handleMintRewards = async () => {
    try {
      const c = getContract();
      const recipient = recipientAddress || (await signer.getAddress());
      const tx = await c.checkAndMintRewards(recipient);
      await tx.wait();
      onSuccess?.("Rewards minted successfully!");
      handleGetTokenInfo(); // Refresh info
      handleGetPendingRewards(); // Refresh pending
    } catch (e) {
      onError?.(e.message);
    }
  };

  const handleGetUserBalance = async () => {
    try {
      const c = getContract();
      const userAddress = await signer.getAddress();
      const balance = await c.balanceOf(userAddress);
      setUserBalance(balance.toString());
    } catch (e) {
      onError?.(e.message);
    }
  };

  const formatValue = (value, decimals = 18) => {
    return (Number(value) / Math.pow(10, decimals)).toFixed(6);
  };

  const formatTimestamp = (timestamp) => {
    if (timestamp === "0") return "Never";
    return new Date(Number(timestamp) * 1000).toLocaleString();
  };

  return (
    <Card>
      <Card.Body>
        <Card.Title>Reward Token</Card.Title>
        <Form>
          <Form.Group className="mb-3">
            <Form.Label>Token Address</Form.Label>
            <Form.Control
              placeholder="0x..."
              value={tokenAddress}
              onChange={(e) => setTokenAddress(e.target.value)}
            />
          </Form.Group>

          <div className="d-flex gap-2 mb-3">
            <Button variant="primary" onClick={handleGetTokenInfo}>
              Get Token Info
            </Button>
            <Button variant="info" onClick={handleGetPendingRewards}>
              Get Pending Rewards
            </Button>
            <Button variant="success" onClick={handleGetUserBalance}>
              Get My Balance
            </Button>
          </div>

          {tokenInfo && (
            <Card className="mt-3">
              <Card.Header>Token Information</Card.Header>
              <Card.Body>
                <Row>
                  <Col md={6}>
                    <div>
                      <strong>Geo Index Token:</strong>{" "}
                      {tokenInfo.geoIndexToken}
                    </div>
                    <div>
                      <strong>Last Index Value:</strong>{" "}
                      {formatValue(tokenInfo.lastIndexValue)}
                    </div>
                    <div>
                      <strong>Mint Rate:</strong>{" "}
                      {formatValue(tokenInfo.mintRate)}
                    </div>
                    <div>
                      <strong>Max Total Supply:</strong>{" "}
                      {formatValue(tokenInfo.maxTotalSupply)}
                    </div>
                  </Col>
                  <Col md={6}>
                    <div>
                      <strong>Total Minted:</strong>{" "}
                      {formatValue(tokenInfo.totalMinted)}
                    </div>
                    <div>
                      <strong>Last Mint:</strong>{" "}
                      {formatTimestamp(tokenInfo.lastMintTimestamp)}
                    </div>
                    <div>
                      <strong>Minting Enabled:</strong>
                      <span
                        className={
                          tokenInfo.mintingEnabled
                            ? "text-success"
                            : "text-warning"
                        }
                      >
                        {tokenInfo.mintingEnabled ? " Yes" : " No"}
                      </span>
                    </div>
                  </Col>
                </Row>
              </Card.Body>
            </Card>
          )}

          {pendingRewards !== null && (
            <Alert variant="info" className="mt-3">
              <strong>Pending Rewards:</strong> {formatValue(pendingRewards)}{" "}
              tokens
            </Alert>
          )}

          {userBalance !== null && (
            <Alert variant="success" className="mt-3">
              <strong>Your Balance:</strong> {formatValue(userBalance)} tokens
            </Alert>
          )}

          <Form.Group className="mb-3">
            <Form.Label>
              Recipient Address (optional, defaults to your address)
            </Form.Label>
            <Form.Control
              placeholder="0x..."
              value={recipientAddress}
              onChange={(e) => setRecipientAddress(e.target.value)}
            />
          </Form.Group>

          <Button variant="warning" onClick={handleMintRewards}>
            Mint Rewards
          </Button>
        </Form>
      </Card.Body>
    </Card>
  );
}
