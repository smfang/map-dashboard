import React, { useState, useEffect } from "react";
import { Card, Form, Button, Row, Col, Alert, Badge } from "react-bootstrap";
import { ethers } from "ethers";

// Contract ABI for minting
const NFT_ABI = [
  "function name() view returns (string)",
  "function symbol() view returns (string)",
  "function maxSupply() view returns (uint256)",
  "function mintPrice() view returns (uint256)",
  "function totalSupply() view returns (uint256)",
  "function mint(string memory tokenURI) public payable returns (uint256)",
  "function ownerMint(address to, string memory tokenURI) public returns (uint256)",
];

const NFTMinting = ({ signer, contracts, onSuccess, onError }) => {
  const [nftContract, setNftContract] = useState(null);
  const [contractInfo, setContractInfo] = useState({});
  const [mintForm, setMintForm] = useState({
    tokenURI: "",
    recipient: "",
  });
  const [loading, setLoading] = useState(false);
  const [userBalance, setUserBalance] = useState("0");
  const [userNFTs, setUserNFTs] = useState([]);

  useEffect(() => {
    if (signer && contracts.nftCollection) {
      initializeContract();
    }
  }, [signer, contracts.nftCollection]);

  const initializeContract = async () => {
    try {
      const contract = new ethers.Contract(
        contracts.nftCollection,
        NFT_ABI,
        signer
      );
      setNftContract(contract);

      // Load contract info
      const [name, symbol, maxSupply, mintPrice, totalSupply] =
        await Promise.all([
          contract.name(),
          contract.symbol(),
          contract.maxSupply(),
          contract.mintPrice(),
          contract.totalSupply(),
        ]);

      setContractInfo({
        name,
        symbol,
        maxSupply: maxSupply.toString(),
        mintPrice: ethers.utils.formatEther(mintPrice),
        totalSupply: totalSupply.toString(),
      });

      // Load user balance
      const balance = await signer.getBalance();
      setUserBalance(ethers.utils.formatEther(balance));

      // Load user's NFTs (if any)
      await loadUserNFTs(contract);
    } catch (error) {
      onError("Failed to initialize contract: " + error.message);
    }
  };

  const loadUserNFTs = async (contract) => {
    try {
      // This is a simplified approach - in a real app you'd want to track token IDs
      const totalSupply = await contract.totalSupply();
      const userAddress = await signer.getAddress();

      // For now, we'll just show the total supply info
      // In a real implementation, you'd query for tokens owned by the user
      setUserNFTs([{ totalSupply: totalSupply.toString() }]);
    } catch (error) {
      console.error("Error loading user NFTs:", error);
    }
  };

  const handleMintFormChange = (field, value) => {
    setMintForm((prev) => ({
      ...prev,
      [field]: value,
    }));
  };

  const mintNFT = async () => {
    if (!nftContract || !mintForm.tokenURI) {
      onError("Please provide a token URI");
      return;
    }

    setLoading(true);

    try {
      const mintPrice = ethers.utils.parseEther(contractInfo.mintPrice);
      const mintPriceWei = ethers.utils.parseEther(contractInfo.mintPrice);

      // Check if user has enough balance
      const userBalanceWei = ethers.utils.parseEther(userBalance);
      if (userBalanceWei.lt(mintPriceWei)) {
        onError("Insufficient balance to mint NFT");
        setLoading(false);
        return;
      }

      // Mint the NFT
      const tx = await nftContract.mint(mintForm.tokenURI, {
        value: mintPriceWei,
      });

      onSuccess(`NFT minting transaction sent! Hash: ${tx.hash}`);

      // Wait for confirmation
      const receipt = await tx.wait();
      onSuccess(
        `NFT minted successfully! Transaction confirmed in block ${receipt.blockNumber}`
      );

      // Reset form and reload data
      setMintForm({ tokenURI: "", recipient: "" });
      await initializeContract();
    } catch (error) {
      onError("Failed to mint NFT: " + error.message);
    } finally {
      setLoading(false);
    }
  };

  const ownerMint = async () => {
    if (!nftContract || !mintForm.tokenURI || !mintForm.recipient) {
      onError("Please provide both token URI and recipient address");
      return;
    }

    if (!ethers.utils.isAddress(mintForm.recipient)) {
      onError("Invalid recipient address");
      return;
    }

    setLoading(true);

    try {
      // Owner mint (free)
      const tx = await nftContract.ownerMint(
        mintForm.recipient,
        mintForm.tokenURI
      );

      onSuccess(`Owner mint transaction sent! Hash: ${tx.hash}`);

      // Wait for confirmation
      const receipt = await tx.wait();
      onSuccess(
        `NFT minted successfully for ${mintForm.recipient}! Transaction confirmed in block ${receipt.blockNumber}`
      );

      // Reset form and reload data
      setMintForm({ tokenURI: "", recipient: "" });
      await initializeContract();
    } catch (error) {
      onError("Failed to owner mint NFT: " + error.message);
    } finally {
      setLoading(false);
    }
  };

  if (!contracts.nftCollection) {
    return (
      <Alert variant="warning">
        Please set the NFT Collection address in the Contract Info tab first.
      </Alert>
    );
  }

  if (!nftContract) {
    return <Alert variant="info">Loading contract information...</Alert>;
  }

  return (
    <div>
      <h2 className="mb-4">🎨 Mint NFT</h2>

      {/* Contract Information */}
      <Card className="mb-4">
        <Card.Header>
          <h5>📋 Collection Information</h5>
        </Card.Header>
        <Card.Body>
          <Row>
            <Col md={6}>
              <strong>Name:</strong> {contractInfo.name}
            </Col>
            <Col md={6}>
              <strong>Symbol:</strong> {contractInfo.symbol}
            </Col>
          </Row>
          <Row className="mt-3">
            <Col md={4}>
              <strong>Max Supply:</strong> {contractInfo.maxSupply}
            </Col>
            <Col md={4}>
              <strong>Total Supply:</strong> {contractInfo.totalSupply}
            </Col>
            <Col md={4}>
              <strong>Mint Price:</strong> {contractInfo.mintPrice} ETH
            </Col>
          </Row>
          <Row className="mt-3">
            <Col md={6}>
              <strong>Your Balance:</strong> {userBalance} ETH
            </Col>
            <Col md={6}>
              <strong>Available to Mint:</strong>{" "}
              {parseInt(contractInfo.maxSupply) -
                parseInt(contractInfo.totalSupply)}
            </Col>
          </Row>
        </Card.Body>
      </Card>

      {/* Minting Forms */}
      <Row>
        {/* Public Mint */}
        <Col md={6}>
          <Card className="mb-4">
            <Card.Header>
              <h6>💰 Public Mint (Pay Mint Price)</h6>
            </Card.Header>
            <Card.Body>
              <Form.Group className="mb-3">
                <Form.Label>Token URI (Metadata)</Form.Label>
                <Form.Control
                  type="text"
                  placeholder="https://api.example.com/metadata/1"
                  value={mintForm.tokenURI}
                  onChange={(e) =>
                    handleMintFormChange("tokenURI", e.target.value)
                  }
                />
                <Form.Text className="text-muted">
                  URL to the NFT metadata (JSON file with name, description,
                  image, etc.)
                </Form.Text>
              </Form.Group>

              <Button
                onClick={mintNFT}
                variant="primary"
                disabled={loading || !mintForm.tokenURI}
                className="w-100"
              >
                {loading
                  ? "Minting..."
                  : `Mint NFT (${contractInfo.mintPrice} ETH)`}
              </Button>

              <div className="mt-2">
                <small className="text-muted">
                  Cost: {contractInfo.mintPrice} ETH + gas fees
                </small>
              </div>
            </Card.Body>
          </Card>
        </Col>

        {/* Owner Mint */}
        <Col md={6}>
          <Card className="mb-4">
            <Card.Header>
              <h6>👑 Owner Mint (Free)</h6>
            </Card.Header>
            <Card.Body>
              <Form.Group className="mb-3">
                <Form.Label>Token URI (Metadata)</Form.Label>
                <Form.Control
                  type="text"
                  placeholder="https://api.example.com/metadata/1"
                  value={mintForm.tokenURI}
                  onChange={(e) =>
                    handleMintFormChange("tokenURI", e.target.value)
                  }
                />
              </Form.Group>

              <Form.Group className="mb-3">
                <Form.Label>Recipient Address</Form.Label>
                <Form.Control
                  type="text"
                  placeholder="0x..."
                  value={mintForm.recipient}
                  onChange={(e) =>
                    handleMintFormChange("recipient", e.target.value)
                  }
                />
                <Form.Text className="text-muted">
                  Address to receive the minted NFT
                </Form.Text>
              </Form.Group>

              <Button
                onClick={ownerMint}
                variant="outline-primary"
                disabled={loading || !mintForm.tokenURI || !mintForm.recipient}
                className="w-100"
              >
                {loading ? "Minting..." : "Owner Mint NFT (Free)"}
              </Button>

              <div className="mt-2">
                <small className="text-muted">
                  Only works if you're the contract owner
                </small>
              </div>
            </Card.Body>
          </Card>
        </Col>
      </Row>

      {/* User's NFTs */}
      {userNFTs.length > 0 && (
        <Card className="mb-4">
          <Card.Header>
            <h5>🎭 Your NFTs</h5>
          </Card.Header>
          <Card.Body>
            <p>Total NFTs in collection: {userNFTs[0]?.totalSupply || 0}</p>
            <Alert variant="info">
              <strong>Note:</strong> This shows the total supply of the
              collection. To see your specific NFTs, you would need to implement
              token ownership tracking.
            </Alert>
          </Card.Body>
        </Card>
      )}

      {/* Help Information */}
      <Card className="mb-4">
        <Card.Header>
          <h5>💡 How to Mint</h5>
        </Card.Header>
        <Card.Body>
          <ol>
            <li>
              <strong>Prepare Metadata:</strong> Create a JSON file with your
              NFT details (name, description, image URL)
            </li>
            <li>
              <strong>Host Metadata:</strong> Upload the JSON file to IPFS,
              Arweave, or your own server
            </li>
            <li>
              <strong>Copy URI:</strong> Use the full URL to your metadata file
            </li>
            <li>
              <strong>Mint:</strong> Paste the URI and click mint (make sure you
              have enough ETH for the mint price + gas)
            </li>
          </ol>

          <div className="mt-3">
            <strong>Example Metadata:</strong>
            <pre className="bg-light p-2 mt-2 rounded">
              {`{
  "name": "My Awesome NFT",
  "description": "This is a description of my NFT",
  "image": "https://ipfs.io/ipfs/QmYwAPJzv5CZsnA625s3Xf2nemtYgPpHdWEz79ojWnPbdG",
  "attributes": [
    {
      "trait_type": "Background",
      "value": "Blue"
    }
  ]
}`}
            </pre>
          </div>
        </Card.Body>
      </Card>
    </div>
  );
};

export default NFTMinting;
