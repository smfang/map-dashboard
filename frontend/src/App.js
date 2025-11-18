import React, { useState, useEffect } from "react";
import { Container, Navbar, Nav, Button, Alert } from "react-bootstrap";
import { ethers } from "ethers";
import detectEthereumProvider from "@metamask/detect-provider";
import "./App.css";

// Import components
import WalletConnect from "./components/WalletConnect";
import NFTMinting from "./components/NFTMinting";
import VaultManagement from "./components/VaultManagement";
import ContractInfo from "./components/ContractInfo";
import UMAOracle from "./components/UMAOracle";
import CarbonIndexView from "./components/CarbonIndexView";
import GeoIndexTokenView from "./components/GeoIndexTokenView";
import NatureIndexTracker from "./components/NatureIndexTracker";
import RewardTokenView from "./components/RewardTokenView";
import SP1ProofStatus from "./components/SP1ProofStatus";

function App() {
  const [provider, setProvider] = useState(null);
  const [signer, setSigner] = useState(null);
  const [account, setAccount] = useState(null);
  const [network, setNetwork] = useState(null);
  const [activeTab, setActiveTab] = useState("info");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  // Contract addresses - update these after deployment
  const [contracts, setContracts] = useState({
    nftFactory: "",
    nftCollection: "",
    vault: "",
  });

  useEffect(() => {
    initializeProvider();
  }, []);

  const initializeProvider = async () => {
    try {
      const detectedProvider = await detectEthereumProvider();

      if (detectedProvider) {
        setProvider(detectedProvider);

        // Listen for account changes
        detectedProvider.on("accountsChanged", (accounts) => {
          if (accounts.length > 0) {
            setAccount(accounts[0]);
          } else {
            setAccount(null);
            setSigner(null);
          }
        });

        // Listen for network changes
        detectedProvider.on("chainChanged", (chainId) => {
          window.location.reload();
        });

        // Check if already connected
        const accounts = await detectedProvider.request({
          method: "eth_accounts",
        });
        if (accounts.length > 0) {
          await connectWallet();
        }
      } else {
        setError("Please install MetaMask to use this app");
      }
    } catch (error) {
      setError("Failed to initialize provider: " + error.message);
    }
  };

  const connectWallet = async () => {
    try {
      if (!provider) {
        setError("Provider not initialized");
        return;
      }

      // Request account access
      const accounts = await provider.request({
        method: "eth_requestAccounts",
      });

      if (accounts.length > 0) {
        const ethersProvider = new ethers.providers.Web3Provider(provider);
        const signer = ethersProvider.getSigner();
        const network = await ethersProvider.getNetwork();

        setSigner(signer);
        setAccount(accounts[0]);
        setNetwork(network);
        setError("");
        setSuccess("Wallet connected successfully!");

        // Clear success message after 3 seconds
        setTimeout(() => setSuccess(""), 3000);
      }
    } catch (error) {
      setError("Failed to connect wallet: " + error.message);
    }
  };

  const disconnectWallet = () => {
    setSigner(null);
    setAccount(null);
    setNetwork(null);
    setSuccess("Wallet disconnected");
    setTimeout(() => setSuccess(""), 3000);
  };

  const updateContractAddresses = (addresses) => {
    setContracts(addresses);
  };

  const renderContent = () => {
    if (!account) {
      return <WalletConnect onConnect={connectWallet} />;
    }

    switch (activeTab) {
      case "mint":
        return (
          <NFTMinting
            signer={signer}
            contracts={contracts}
            onSuccess={setSuccess}
            onError={setError}
          />
        );
      case "vault":
        return (
          <VaultManagement
            signer={signer}
            contracts={contracts}
            onSuccess={setSuccess}
            onError={setError}
          />
        );
      case "uma":
        return (
          <UMAOracle
            signer={signer}
            onSuccess={setSuccess}
            onError={setError}
          />
        );
      case "index":
        return <CarbonIndexView signer={signer} onError={setError} />;
      case "geo":
        return <GeoIndexTokenView signer={signer} onError={setError} />;
      case "nature":
        return (
          <NatureIndexTracker
            signer={signer}
            onSuccess={setSuccess}
            onError={setError}
          />
        );
      case "rewards":
        return (
          <RewardTokenView
            signer={signer}
            onSuccess={setSuccess}
            onError={setError}
          />
        );
      case "sp1":
        return (
          <SP1ProofStatus
            signer={signer}
            onSuccess={setSuccess}
            onError={setError}
          />
        );
      case "info":
      default:
        return (
          <ContractInfo
            signer={signer}
            contracts={contracts}
            onUpdateAddresses={updateContractAddresses}
          />
        );
    }
  };

  return (
    <div className="App">
      <Navbar bg="dark" variant="dark" expand="lg" className="mb-4">
        <Container>
          <Navbar.Brand>🎨 NFT Factory & Vault</Navbar.Brand>
          <Navbar.Toggle aria-controls="basic-navbar-nav" />
          <Navbar.Collapse id="basic-navbar-nav">
            <Nav className="me-auto">
              <Nav.Link
                active={activeTab === "info"}
                onClick={() => setActiveTab("info")}
              >
                Contract Info
              </Nav.Link>
              <Nav.Link
                active={activeTab === "mint"}
                onClick={() => setActiveTab("mint")}
              >
                Mint NFT
              </Nav.Link>
              <Nav.Link
                active={activeTab === "vault"}
                onClick={() => setActiveTab("vault")}
              >
                Vault Management
              </Nav.Link>
              <Nav.Link
                active={activeTab === "uma"}
                onClick={() => setActiveTab("uma")}
              >
                UMA Oracle
              </Nav.Link>
              <Nav.Link
                active={activeTab === "index"}
                onClick={() => setActiveTab("index")}
              >
                Carbon Index
              </Nav.Link>
              <Nav.Link
                active={activeTab === "geo"}
                onClick={() => setActiveTab("geo")}
              >
                Geo Index Token
              </Nav.Link>
              <Nav.Link
                active={activeTab === "nature"}
                onClick={() => setActiveTab("nature")}
              >
                Nature Index Tracker
              </Nav.Link>
              <Nav.Link
                active={activeTab === "rewards"}
                onClick={() => setActiveTab("rewards")}
              >
                Reward Token
              </Nav.Link>
              <Nav.Link
                active={activeTab === "sp1"}
                onClick={() => setActiveTab("sp1")}
              >
                SP1 Proof Status
              </Nav.Link>
            </Nav>
            <Nav>
              {account ? (
                <div className="d-flex align-items-center">
                  <span className="text-light me-3">
                    {account.slice(0, 6)}...{account.slice(-4)}
                  </span>
                  <Button
                    variant="outline-light"
                    size="sm"
                    onClick={disconnectWallet}
                  >
                    Disconnect
                  </Button>
                </div>
              ) : (
                <Button variant="outline-light" onClick={connectWallet}>
                  Connect Wallet
                </Button>
              )}
            </Nav>
          </Navbar.Collapse>
        </Container>
      </Navbar>

      <Container>
        {error && (
          <Alert variant="danger" dismissible onClose={() => setError("")}>
            {error}
          </Alert>
        )}

        {success && (
          <Alert variant="success" dismissible onClose={() => setSuccess("")}>
            {success}
          </Alert>
        )}

        {network && (
          <Alert variant="info" className="mb-3">
            Connected to: {network.name} (Chain ID: {network.chainId})
          </Alert>
        )}

        {renderContent()}
      </Container>
    </div>
  );
}

export default App;
