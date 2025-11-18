import React, { useState, useEffect } from "react";
import { Card, Form, Button, Row, Col, Alert, Badge } from "react-bootstrap";
import { ethers } from "ethers";

// Contract ABIs (simplified for frontend)
const NFT_FACTORY_ABI = [
  "function getTotalCollections() view returns (uint256)",
  "function getDeployedNFTs() view returns (address[])",
  "function getNFTVault(address nftAddress) view returns (address)",
];

const NFT_ABI = [
  "function name() view returns (string)",
  "function symbol() view returns (string)",
  "function maxSupply() view returns (uint256)",
  "function mintPrice() view returns (uint256)",
  "function totalSupply() view returns (uint256)",
];

const VAULT_ABI = [
  "function vaultName() view returns (string)",
  "function vaultSymbol() view returns (string)",
  "function vaultActive() view returns (bool)",
  "function totalAssets() view returns (uint256)",
  "function totalSupply() view returns (uint256)",
  "function maxDepositLimit() view returns (uint256)",
  "function currentDepositLimit() view returns (uint256)",
];

const ContractInfo = ({ signer, contracts, onUpdateAddresses }) => {
  const [addresses, setAddresses] = useState({
    nftFactory: contracts.nftFactory || "",
    nftCollection: contracts.nftCollection || "",
    vault: contracts.vault || "",
  });

  const [contractInfo, setContractInfo] = useState({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (signer && addresses.nftFactory) {
      loadContractInfo();
    }
  }, [signer, addresses.nftFactory]);

  const handleAddressChange = (field, value) => {
    setAddresses((prev) => ({
      ...prev,
      [field]: value,
    }));
  };

  const updateAddresses = () => {
    onUpdateAddresses(addresses);
  };

  const loadContractInfo = async () => {
    if (!signer || !addresses.nftFactory) return;

    setLoading(true);
    setError("");

    try {
      const factory = new ethers.Contract(
        addresses.nftFactory,
        NFT_FACTORY_ABI,
        signer
      );

      // Get factory info
      const totalCollections = await factory.getTotalCollections();
      const deployedNFTs = await factory.getDeployedNFTs();

      const info = {
        factory: {
          totalCollections: totalCollections.toString(),
          deployedNFTs: deployedNFTs,
        },
      };

      // If we have NFT collection address, get its info
      if (
        addresses.nftCollection &&
        ethers.utils.isAddress(addresses.nftCollection)
      ) {
        try {
          const nftContract = new ethers.Contract(
            addresses.nftCollection,
            NFT_ABI,
            signer
          );
          const vaultAddress = await factory.getNFTVault(
            addresses.nftCollection
          );

          const [name, symbol, maxSupply, mintPrice, totalSupply] =
            await Promise.all([
              nftContract.name(),
              nftContract.symbol(),
              nftContract.maxSupply(),
              nftContract.mintPrice(),
              nftContract.totalSupply(),
            ]);

          info.nft = {
            name,
            symbol,
            maxSupply: maxSupply.toString(),
            mintPrice: ethers.utils.formatEther(mintPrice),
            totalSupply: totalSupply.toString(),
            vaultAddress,
          };

          // Update vault address if found
          if (vaultAddress !== ethers.constants.AddressZero) {
            setAddresses((prev) => ({ ...prev, vault: vaultAddress }));
          }
        } catch (error) {
          console.error("Error loading NFT info:", error);
        }
      }

      // If we have vault address, get its info
      if (addresses.vault && ethers.utils.isAddress(addresses.vault)) {
        try {
          const vaultContract = new ethers.Contract(
            addresses.vault,
            VAULT_ABI,
            signer
          );

          const [
            vaultName,
            vaultSymbol,
            vaultActive,
            totalAssets,
            totalShares,
            maxDepositLimit,
            currentDepositLimit,
          ] = await Promise.all([
            vaultContract.vaultName(),
            vaultContract.vaultSymbol(),
            vaultContract.vaultActive(),
            vaultContract.totalAssets(),
            vaultContract.totalSupply(),
            vaultContract.maxDepositLimit(),
            vaultContract.currentDepositLimit(),
          ]);

          info.vault = {
            name: vaultName,
            symbol: vaultSymbol,
            active: vaultActive,
            totalAssets: ethers.utils.formatEther(totalAssets),
            totalShares: totalShares.toString(),
            maxDepositLimit: ethers.utils.formatEther(maxDepositLimit),
            currentDepositLimit: ethers.utils.formatEther(currentDepositLimit),
          };
        } catch (error) {
          console.error("Error loading vault info:", error);
        }
      }

      setContractInfo(info);
    } catch (error) {
      setError("Failed to load contract info: " + error.message);
    } finally {
      setLoading(false);
    }
  };

  const refreshInfo = () => {
    loadContractInfo();
  };

  return (
    <div>
      <h2 className="mb-4">📋 Contract Information</h2>

      <Card className="mb-4">
        <Card.Header>
          <h5>🔧 Contract Addresses</h5>
        </Card.Header>
        <Card.Body>
          <Row>
            <Col md={4}>
              <Form.Group className="mb-3">
                <Form.Label>NFT Factory Address</Form.Label>
                <Form.Control
                  type="text"
                  placeholder="0x..."
                  value={addresses.nftFactory}
                  onChange={(e) =>
                    handleAddressChange("nftFactory", e.target.value)
                  }
                />
                <Form.Text className="text-muted">
                  Address of the deployed NFT Factory contract
                </Form.Text>
              </Form.Group>
            </Col>
            <Col md={4}>
              <Form.Group className="mb-3">
                <Form.Label>NFT Collection Address</Form.Label>
                <Form.Control
                  type="text"
                  placeholder="0x..."
                  value={addresses.nftCollection}
                  onChange={(e) =>
                    handleAddressChange("nftCollection", e.target.value)
                  }
                />
                <Form.Text className="text-muted">
                  Address of the NFT collection you want to interact with
                </Form.Text>
              </Form.Group>
            </Col>
            <Col md={4}>
              <Form.Group className="mb-3">
                <Form.Label>Vault Address</Form.Label>
                <Form.Control
                  type="text"
                  placeholder="0x..."
                  value={addresses.vault}
                  onChange={(e) => handleAddressChange("vault", e.target.value)}
                />
                <Form.Text className="text-muted">
                  Address of the vault associated with the NFT collection
                </Form.Text>
              </Form.Group>
            </Col>
          </Row>

          <div className="d-flex gap-2">
            <Button onClick={updateAddresses} variant="primary">
              Update Addresses
            </Button>
            <Button
              onClick={refreshInfo}
              variant="outline-secondary"
              disabled={loading}
            >
              {loading ? "Loading..." : "Refresh Info"}
            </Button>
          </div>
        </Card.Body>
      </Card>

      {error && (
        <Alert variant="danger" dismissible onClose={() => setError("")}>
          {error}
        </Alert>
      )}

      {/* Factory Information */}
      {contractInfo.factory && (
        <Card className="mb-4">
          <Card.Header>
            <h5>🏭 Factory Information</h5>
          </Card.Header>
          <Card.Body>
            <Row>
              <Col md={6}>
                <strong>Total Collections:</strong>{" "}
                {contractInfo.factory.totalCollections}
              </Col>
              <Col md={6}>
                <strong>Deployed NFTs:</strong>{" "}
                {contractInfo.factory.deployedNFTs.length}
              </Col>
            </Row>
            {contractInfo.factory.deployedNFTs.length > 0 && (
              <div className="mt-3">
                <strong>NFT Addresses:</strong>
                <div className="mt-2">
                  {contractInfo.factory.deployedNFTs.map((address, index) => (
                    <Badge key={index} bg="secondary" className="me-2">
                      {address.slice(0, 6)}...{address.slice(-4)}
                    </Badge>
                  ))}
                </div>
              </div>
            )}
          </Card.Body>
        </Card>
      )}

      {/* NFT Information */}
      {contractInfo.nft && (
        <Card className="mb-4">
          <Card.Header>
            <h5>🎨 NFT Collection Information</h5>
          </Card.Header>
          <Card.Body>
            <Row>
              <Col md={6}>
                <strong>Name:</strong> {contractInfo.nft.name}
              </Col>
              <Col md={6}>
                <strong>Symbol:</strong> {contractInfo.nft.symbol}
              </Col>
            </Row>
            <Row className="mt-3">
              <Col md={4}>
                <strong>Max Supply:</strong> {contractInfo.nft.maxSupply}
              </Col>
              <Col md={4}>
                <strong>Total Supply:</strong> {contractInfo.nft.totalSupply}
              </Col>
              <Col md={4}>
                <strong>Mint Price:</strong> {contractInfo.nft.mintPrice} ETH
              </Col>
            </Row>
            {contractInfo.nft.vaultAddress &&
              contractInfo.nft.vaultAddress !==
                ethers.constants.AddressZero && (
                <div className="mt-3">
                  <strong>Associated Vault:</strong>{" "}
                  <Badge bg="info">
                    {contractInfo.nft.vaultAddress.slice(0, 6)}...
                    {contractInfo.nft.vaultAddress.slice(-4)}
                  </Badge>
                </div>
              )}
          </Card.Body>
        </Card>
      )}

      {/* Vault Information */}
      {contractInfo.vault && (
        <Card className="mb-4">
          <Card.Header>
            <h5>🏦 Vault Information</h5>
          </Card.Header>
          <Card.Body>
            <Row>
              <Col md={6}>
                <strong>Name:</strong> {contractInfo.vault.name}
              </Col>
              <Col md={6}>
                <strong>Symbol:</strong> {contractInfo.vault.symbol}
              </Col>
            </Row>
            <Row className="mt-3">
              <Col md={4}>
                <strong>Status:</strong>{" "}
                <Badge bg={contractInfo.vault.active ? "success" : "danger"}>
                  {contractInfo.vault.active ? "Active" : "Inactive"}
                </Badge>
              </Col>
              <Col md={4}>
                <strong>Total Assets:</strong> {contractInfo.vault.totalAssets}{" "}
                ETH
              </Col>
              <Col md={4}>
                <strong>Total Shares:</strong> {contractInfo.vault.totalShares}
              </Col>
            </Row>
            <Row className="mt-3">
              <Col md={6}>
                <strong>Current Deposits:</strong>{" "}
                {contractInfo.vault.currentDepositLimit} ETH
              </Col>
              <Col md={6}>
                <strong>Max Deposit Limit:</strong>{" "}
                {contractInfo.vault.maxDepositLimit} ETH
              </Col>
            </Row>
          </Card.Body>
        </Card>
      )}

      {!contractInfo.factory && !loading && (
        <Alert variant="info">
          Enter the NFT Factory address above to load contract information.
        </Alert>
      )}
    </div>
  );
};

export default ContractInfo;
