import React from "react";
import { Card, Button, Alert } from "react-bootstrap";

const WalletConnect = ({ onConnect }) => {
  return (
    <div
      className="d-flex justify-content-center align-items-center"
      style={{ minHeight: "60vh" }}
    >
      <Card style={{ width: "400px" }}>
        <Card.Header className="text-center">
          <h4>🔗 Connect Your Wallet</h4>
        </Card.Header>
        <Card.Body className="text-center">
          <Card.Text>
            To interact with NFT contracts and vaults, you need to connect your
            MetaMask wallet.
          </Card.Text>

          <Alert variant="info" className="mb-3">
            <strong>Requirements:</strong>
            <ul className="mb-0 mt-2">
              <li>MetaMask extension installed</li>
              <li>Account with some ETH for gas fees</li>
              <li>Connected to the correct network</li>
            </ul>
          </Alert>

          <Button
            variant="primary"
            size="lg"
            onClick={onConnect}
            className="w-100"
          >
            🦊 Connect MetaMask
          </Button>

          <div className="mt-3">
            <small className="text-muted">
              Don't have MetaMask?{" "}
              <a
                href="https://metamask.io/download/"
                target="_blank"
                rel="noopener noreferrer"
              >
                Download here
              </a>
            </small>
          </div>
        </Card.Body>
      </Card>
    </div>
  );
};

export default WalletConnect;
