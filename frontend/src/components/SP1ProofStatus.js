import React, { useState, useEffect } from "react";
import { Button, Card, Row, Col, Alert, Spinner } from "react-bootstrap";
import { ethers } from "ethers";

const SP1_VERIFIER_ABI = [
  {
    inputs: [{ internalType: "bytes32", name: "proofHash", type: "bytes32" }],
    name: "isProofVerified",
    outputs: [{ internalType: "bool", name: "", type: "bool" }],
    stateMutability: "view",
    type: "function",
  },
  {
    inputs: [{ internalType: "bytes32", name: "proofHash", type: "bytes32" }],
    name: "isProofSubmitted",
    outputs: [{ internalType: "bool", name: "", type: "bool" }],
    stateMutability: "view",
    type: "function",
  },
  {
    inputs: [{ internalType: "bytes32", name: "proofHash", type: "bytes32" }],
    name: "getZKVerifyProofId",
    outputs: [{ internalType: "bytes32", name: "", type: "bytes32" }],
    stateMutability: "view",
    type: "function",
  },
  {
    inputs: [{ internalType: "bytes32", name: "proofHash", type: "bytes32" }],
    name: "finalizeProof",
    outputs: [],
    stateMutability: "nonpayable",
    type: "function",
  },
  {
    inputs: [{ internalType: "bytes32", name: "proofHash", type: "bytes32" }],
    name: "getCarbonIndexValue",
    outputs: [{ internalType: "uint256", name: "", type: "uint256" }],
    stateMutability: "view",
    type: "function",
  },
];

export default function SP1ProofStatus({ signer, onSuccess, onError }) {
  const [verifierAddress, setVerifierAddress] = useState("");
  const [proofHash, setProofHash] = useState("");
  const [proofStatus, setProofStatus] = useState(null);
  const [loading, setLoading] = useState(false);
  const [polling, setPolling] = useState(false);

  const checkProofStatus = async () => {
    if (!signer || !verifierAddress || !proofHash) return;

    try {
      setLoading(true);
      const contract = new ethers.Contract(
        verifierAddress,
        SP1_VERIFIER_ABI,
        signer
      );

      const [isVerified, isSubmitted, zkVerifyProofId] = await Promise.all([
        contract.isProofVerified(proofHash),
        contract.isProofSubmitted(proofHash),
        contract.getZKVerifyProofId(proofHash),
      ]);

      let carbonIndexValue = null;
      if (isVerified) {
        carbonIndexValue = await contract.getCarbonIndexValue(proofHash);
      }

      setProofStatus({
        isVerified,
        isSubmitted,
        zkVerifyProofId:
          zkVerifyProofId !== ethers.constants.HashZero
            ? zkVerifyProofId
            : null,
        carbonIndexValue,
      });
    } catch (error) {
      console.error("Error checking proof status:", error);
      onError && onError(error.message);
    } finally {
      setLoading(false);
    }
  };

  const finalizeProof = async () => {
    if (!signer || !verifierAddress || !proofHash) return;

    try {
      setLoading(true);
      const contract = new ethers.Contract(
        verifierAddress,
        SP1_VERIFIER_ABI,
        signer
      );

      const tx = await contract.finalizeProof(proofHash);
      await tx.wait();

      onSuccess && onSuccess("Proof finalized successfully!");
      await checkProofStatus(); // Refresh status
    } catch (error) {
      console.error("Error finalizing proof:", error);
      onError && onError(error.message);
    } finally {
      setLoading(false);
    }
  };

  const startPolling = () => {
    if (polling) return;

    setPolling(true);
    const interval = setInterval(async () => {
      await checkProofStatus();

      // Stop polling if proof is verified
      if (proofStatus?.isVerified) {
        setPolling(false);
        clearInterval(interval);
      }
    }, 5000); // Poll every 5 seconds

    // Store interval ID for cleanup
    setPolling(interval);
  };

  const stopPolling = () => {
    if (polling && typeof polling === "number") {
      clearInterval(polling);
      setPolling(false);
    }
  };

  useEffect(() => {
    return () => {
      stopPolling();
    };
  }, []);

  const getStatusBadge = () => {
    if (!proofStatus) return null;

    if (proofStatus.isVerified) {
      return <Alert variant="success">✓ Proof Verified</Alert>;
    } else if (proofStatus.isSubmitted) {
      return <Alert variant="warning">⏳ Submitted to ZKVerify</Alert>;
    } else {
      return <Alert variant="info">📝 Not Submitted</Alert>;
    }
  };

  return (
    <Card>
      <Card.Header>
        <h5>SP1 Proof Status Tracker</h5>
      </Card.Header>
      <Card.Body>
        <Row className="mb-3">
          <Col md={6}>
            <label className="form-label">SP1Verifier Contract Address:</label>
            <input
              type="text"
              className="form-control"
              value={verifierAddress}
              onChange={(e) => setVerifierAddress(e.target.value)}
              placeholder="0x..."
            />
          </Col>
          <Col md={6}>
            <label className="form-label">Proof Hash:</label>
            <input
              type="text"
              className="form-control"
              value={proofHash}
              onChange={(e) => setProofHash(e.target.value)}
              placeholder="0x..."
            />
          </Col>
        </Row>

        <Row className="mb-3">
          <Col>
            <Button
              onClick={checkProofStatus}
              disabled={loading || !signer || !verifierAddress || !proofHash}
              className="me-2"
            >
              {loading ? <Spinner size="sm" /> : "Check Status"}
            </Button>

            {proofStatus?.isSubmitted && !proofStatus?.isVerified && (
              <Button
                onClick={finalizeProof}
                disabled={loading}
                variant="success"
                className="me-2"
              >
                {loading ? <Spinner size="sm" /> : "Finalize Proof"}
              </Button>
            )}

            {proofStatus?.isSubmitted &&
              !proofStatus?.isVerified &&
              !polling && (
                <Button
                  onClick={startPolling}
                  variant="outline-primary"
                  className="me-2"
                >
                  Start Polling
                </Button>
              )}

            {polling && (
              <Button onClick={stopPolling} variant="outline-secondary">
                Stop Polling
              </Button>
            )}
          </Col>
        </Row>

        {proofStatus && (
          <Row>
            <Col>
              {getStatusBadge()}

              {proofStatus.zkVerifyProofId && (
                <Alert variant="info" className="mt-2">
                  <strong>ZKVerify Proof ID:</strong>
                  <br />
                  <code>{proofStatus.zkVerifyProofId}</code>
                </Alert>
              )}

              {proofStatus.carbonIndexValue && (
                <Alert variant="success" className="mt-2">
                  <strong>Carbon Index Value:</strong>
                  <br />
                  {ethers.utils.formatEther(proofStatus.carbonIndexValue)}
                </Alert>
              )}

              {polling && (
                <Alert variant="info" className="mt-2">
                  <Spinner size="sm" className="me-2" />
                  Polling for verification updates...
                </Alert>
              )}
            </Col>
          </Row>
        )}
      </Card.Body>
    </Card>
  );
}
