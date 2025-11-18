import React, { useState, useEffect } from "react";
import {
  Card,
  Form,
  Button,
  Row,
  Col,
  Alert,
  Badge,
  ProgressBar,
} from "react-bootstrap";
import { ethers } from "ethers";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";

// Contract ABI for vault operations
const VAULT_ABI = [
  "function vaultName() view returns (string)",
  "function vaultSymbol() view returns (string)",
  "function vaultActive() view returns (bool)",
  "function totalAssets() view returns (uint256)",
  "function totalSupply() view returns (uint256)",
  "function maxDepositLimit() view returns (uint256)",
  "function currentDepositLimit() view returns (uint256)",
  "function balanceOf(address owner) view returns (uint256)",
  "function depositETH(address receiver) public payable returns (uint256)",
  "function withdraw(uint256 assets, address receiver, address owner) public returns (uint256)",
  "function redeem(uint256 shares, address receiver, address owner) public returns (uint256)",
  "function previewDeposit(uint256 assets) view returns (uint256)",
  "function previewWithdraw(uint256 assets) view returns (uint256)",
  "function previewRedeem(uint256 shares) view returns (uint256)",
  "function maxDeposit(address) view returns (uint256)",
  "function maxWithdraw(address owner) view returns (uint256)",
  "function maxRedeem(address owner) view returns (uint256)",
  "function getProjectInfo() view returns (bytes32, address, address, uint256)",
];

// Carbon Index ABI
const CARBON_INDEX_ABI = [
  "function getIndex() view returns (uint256)",
];

// Reward Token ABI
const REWARD_TOKEN_ABI = [
  "function balanceOf(address account) view returns (uint256)",
  "function decimals() view returns (uint8)",
  "function symbol() view returns (string)",
];

const VaultManagement = ({ signer, contracts, onSuccess, onError }) => {
  const [vaultContract, setVaultContract] = useState(null);
  const [vaultInfo, setVaultInfo] = useState({});
  const [userInfo, setUserInfo] = useState({});
  const [forms, setForms] = useState({
    deposit: { amount: "" },
    withdraw: { amount: "" },
    redeem: { shares: "" },
  });
  const [loading, setLoading] = useState(false);
  const [userBalance, setUserBalance] = useState("0");
  
  // New state for carbon index and rewards
  const [carbonIndexAddress, setCarbonIndexAddress] = useState("");
  const [rewardTokenAddress, setRewardTokenAddress] = useState("");
  const [carbonIndexValue, setCarbonIndexValue] = useState("0");
  const [vaultBalanceValue, setVaultBalanceValue] = useState("0");
  const [rewardTokenBalance, setRewardTokenBalance] = useState("0");
  const [rewardTokenSymbol, setRewardTokenSymbol] = useState("");
  const [historicalData, setHistoricalData] = useState([]);

  useEffect(() => {
    if (signer && contracts.vault) {
      initializeVault();
    }
  }, [signer, contracts.vault]);

  // Load historical data from localStorage on mount
  useEffect(() => {
    const saved = localStorage.getItem(`vaultHistory_${contracts.vault}`);
    if (saved) {
      try {
        setHistoricalData(JSON.parse(saved));
      } catch (e) {
        console.error("Error loading historical data:", e);
      }
    }
  }, [contracts.vault]);

  // Auto-refresh carbon index and balance value
  useEffect(() => {
    if (vaultContract && userInfo.shares) {
      if (carbonIndexAddress) {
        updateCarbonIndexValue();
      }
      updateVaultBalanceValue();
    }
  }, [vaultContract, carbonIndexAddress, userInfo.shares, carbonIndexValue]);

  // Auto-refresh reward token balance
  useEffect(() => {
    if (signer && rewardTokenAddress) {
      updateRewardTokenBalance();
    }
  }, [signer, rewardTokenAddress]);

  // Periodic refresh for balance value (every 30 seconds)
  useEffect(() => {
    if (!vaultContract || !userInfo.shares) return;

    const interval = setInterval(() => {
      if (carbonIndexAddress) {
        updateCarbonIndexValue();
      }
      updateVaultBalanceValue();
      if (rewardTokenAddress) {
        updateRewardTokenBalance();
      }
    }, 30000); // Refresh every 30 seconds

    return () => clearInterval(interval);
  }, [vaultContract, userInfo.shares, carbonIndexAddress, rewardTokenAddress]);

  const initializeVault = async () => {
    try {
      const contract = new ethers.Contract(contracts.vault, VAULT_ABI, signer);
      setVaultContract(contract);

      await loadVaultInfo(contract);
      await loadUserInfo(contract);
    } catch (error) {
      onError("Failed to initialize vault: " + error.message);
    }
  };

  const loadVaultInfo = async (contract) => {
    try {
      const [
        vaultName,
        vaultSymbol,
        vaultActive,
        totalAssets,
        totalShares,
        maxDepositLimit,
        currentDepositLimit,
      ] = await Promise.all([
        contract.vaultName(),
        contract.vaultSymbol(),
        contract.vaultActive(),
        contract.totalAssets(),
        contract.totalSupply(),
        contract.maxDepositLimit(),
        contract.currentDepositLimit(),
      ]);

      setVaultInfo({
        name: vaultName,
        symbol: vaultSymbol,
        active: vaultActive,
        totalAssets: ethers.utils.formatEther(totalAssets),
        totalShares: totalShares.toString(),
        maxDepositLimit: ethers.utils.formatEther(maxDepositLimit),
        currentDepositLimit: ethers.utils.formatEther(currentDepositLimit),
      });
    } catch (error) {
      console.error("Error loading vault info:", error);
    }
  };

  const loadUserInfo = async (contract) => {
    try {
      const userAddress = await signer.getAddress();
      const [userShares, maxDeposit, maxWithdraw, maxRedeem, balance] =
        await Promise.all([
          contract.balanceOf(userAddress),
          contract.maxDeposit(userAddress),
          contract.maxWithdraw(userAddress),
          contract.maxRedeem(userAddress),
          signer.getBalance(),
        ]);

      setUserInfo({
        shares: userShares.toString(),
        maxDeposit: ethers.utils.formatEther(maxDeposit),
        maxWithdraw: ethers.utils.formatEther(maxWithdraw),
        maxRedeem: maxRedeem.toString(),
      });

      setUserBalance(ethers.utils.formatEther(balance));
    } catch (error) {
      console.error("Error loading user info:", error);
    }
  };

  const updateCarbonIndexValue = async () => {
    if (!carbonIndexAddress || !ethers.utils.isAddress(carbonIndexAddress)) {
      return;
    }

    try {
      const carbonIndexContract = new ethers.Contract(
        carbonIndexAddress,
        CARBON_INDEX_ABI,
        signer
      );
      const indexValue = await carbonIndexContract.getIndex();
      const formattedValue = ethers.utils.formatEther(indexValue);
      setCarbonIndexValue(formattedValue);
    } catch (error) {
      console.error("Error fetching carbon index:", error);
    }
  };

  const updateVaultBalanceValue = async () => {
    if (!vaultContract || !userInfo.shares || userInfo.shares === "0") {
      return;
    }

    try {
      // Calculate vault balance value: shares * (totalAssets / totalShares) * carbonIndexMultiplier
      const totalAssets = await vaultContract.totalAssets();
      const totalShares = await vaultContract.totalSupply();
      const userSharesBN = ethers.BigNumber.from(userInfo.shares);
      
      if (totalShares.gt(0)) {
        // User's share of assets
        const userAssetShare = totalAssets.mul(userSharesBN).div(totalShares);
        const userAssetShareETH = parseFloat(ethers.utils.formatEther(userAssetShare));
        
        // Multiply by carbon index (as a multiplier, assuming 1.0 = 100% baseline)
        // If carbon index is not set, use 1.0 (no adjustment)
        const carbonMultiplier = carbonIndexValue && carbonIndexValue !== "0" 
          ? parseFloat(carbonIndexValue) 
          : 1.0;
        const adjustedValue = userAssetShareETH * carbonMultiplier;
        
        setVaultBalanceValue(adjustedValue.toFixed(6));
        
        // Save to historical data (only if carbon index is set)
        if (carbonIndexValue && carbonIndexValue !== "0") {
          saveHistoricalDataPoint(adjustedValue);
        }
      }
    } catch (error) {
      console.error("Error calculating vault balance value:", error);
    }
  };

  const updateRewardTokenBalance = async () => {
    if (!rewardTokenAddress || !ethers.utils.isAddress(rewardTokenAddress)) {
      return;
    }

    try {
      const rewardTokenContract = new ethers.Contract(
        rewardTokenAddress,
        REWARD_TOKEN_ABI,
        signer
      );
      const userAddress = await signer.getAddress();
      const [balance, decimals, symbol] = await Promise.all([
        rewardTokenContract.balanceOf(userAddress),
        rewardTokenContract.decimals(),
        rewardTokenContract.symbol(),
      ]);

      const formattedBalance = ethers.utils.formatUnits(balance, decimals);
      setRewardTokenBalance(formattedBalance);
      setRewardTokenSymbol(symbol);
    } catch (error) {
      console.error("Error fetching reward token balance:", error);
    }
  };

  const saveHistoricalDataPoint = (value) => {
    const timestamp = new Date().toISOString();
    const newPoint = {
      timestamp,
      time: new Date().toLocaleTimeString(),
      value: parseFloat(value),
    };

    const updated = [...historicalData, newPoint];
    // Keep only last 50 data points
    const trimmed = updated.slice(-50);
    setHistoricalData(trimmed);
    
    // Save to localStorage
    localStorage.setItem(`vaultHistory_${contracts.vault}`, JSON.stringify(trimmed));
  };

  const handleFormChange = (formType, field, value) => {
    setForms((prev) => ({
      ...prev,
      [formType]: {
        ...prev[formType],
        [field]: value,
      },
    }));
  };

  const depositETH = async () => {
    if (!vaultContract || !forms.deposit.amount) {
      onError("Please enter an amount to deposit");
      return;
    }

    const amount = parseFloat(forms.deposit.amount);
    if (isNaN(amount) || amount <= 0) {
      onError("Please enter a valid amount");
      return;
    }

    if (amount > parseFloat(userBalance)) {
      onError("Insufficient balance");
      return;
    }

    setLoading(true);

    try {
      const amountWei = ethers.utils.parseEther(forms.deposit.amount);
      const userAddress = await signer.getAddress();

      // Preview the deposit
      const sharesPreview = await vaultContract.previewDeposit(amountWei);

      // Execute deposit
      const tx = await vaultContract.depositETH(userAddress, {
        value: amountWei,
      });

      onSuccess(`Deposit transaction sent! Hash: ${tx.hash}`);

      // Wait for confirmation
      const receipt = await tx.wait();
      onSuccess(
        `Successfully deposited ${
          forms.deposit.amount
        } ETH! You received ${sharesPreview.toString()} shares. Transaction confirmed in block ${
          receipt.blockNumber
        }`
      );

      // Reset form and reload data
      setForms((prev) => ({ ...prev, deposit: { amount: "" } }));
      await initializeVault();
      // Refresh balance value after deposit (will auto-update via useEffect)
    } catch (error) {
      onError("Failed to deposit: " + error.message);
    } finally {
      setLoading(false);
    }
  };

  const withdrawETH = async () => {
    if (!vaultContract || !forms.withdraw.amount) {
      onError("Please enter an amount to withdraw");
      return;
    }

    const amount = parseFloat(forms.withdraw.amount);
    if (isNaN(amount) || amount <= 0) {
      onError("Please enter a valid amount");
      return;
    }

    if (amount > parseFloat(userInfo.maxWithdraw)) {
      onError("Amount exceeds your maximum withdrawal");
      return;
    }

    setLoading(true);

    try {
      const amountWei = ethers.utils.parseEther(forms.withdraw.amount);
      const userAddress = await signer.getAddress();

      // Execute withdrawal
      const tx = await vaultContract.withdraw(
        amountWei,
        userAddress,
        userAddress
      );

      onSuccess(`Withdrawal transaction sent! Hash: ${tx.hash}`);

      // Wait for confirmation
      const receipt = await tx.wait();
      onSuccess(
        `Successfully withdrew ${forms.withdraw.amount} ETH! Transaction confirmed in block ${receipt.blockNumber}`
      );

      // Reset form and reload data
      setForms((prev) => ({ ...prev, withdraw: { amount: "" } }));
      await initializeVault();
    } catch (error) {
      onError("Failed to withdraw: " + error.message);
    } finally {
      setLoading(false);
    }
  };

  const redeemShares = async () => {
    if (!vaultContract || !forms.redeem.shares) {
      onError("Please enter shares to redeem");
      return;
    }

    const shares = parseFloat(forms.redeem.shares);
    if (isNaN(shares) || shares <= 0) {
      onError("Please enter a valid number of shares");
      return;
    }

    if (shares > parseFloat(userInfo.maxRedeem)) {
      onError("Shares exceed your maximum redemption");
      return;
    }

    setLoading(true);

    try {
      const sharesWei = ethers.utils.parseUnits(forms.redeem.shares, 18);
      const userAddress = await signer.getAddress();

      // Preview the redemption
      const assetsPreview = await vaultContract.previewRedeem(sharesWei);

      // Execute redemption
      const tx = await vaultContract.redeem(
        sharesWei,
        userAddress,
        userAddress
      );

      onSuccess(`Redemption transaction sent! Hash: ${tx.hash}`);

      // Wait for confirmation
      const receipt = await tx.wait();
      onSuccess(
        `Successfully redeemed ${
          forms.redeem.shares
        } shares for ${ethers.utils.formatEther(
          assetsPreview
        )} ETH! Transaction confirmed in block ${receipt.blockNumber}`
      );

      // Reset form and reload data
      setForms((prev) => ({ ...prev, redeem: { shares: "" } }));
      await initializeVault();
    } catch (error) {
      onError("Failed to redeem shares: " + error.message);
    } finally {
      setLoading(false);
    }
  };

  if (!contracts.vault) {
    return (
      <Alert variant="warning">
        Please set the Vault address in the Contract Info tab first.
      </Alert>
    );
  }

  if (!vaultContract) {
    return <Alert variant="info">Loading vault information...</Alert>;
  }

  const depositUtilization =
    (parseFloat(vaultInfo.currentDepositLimit) /
      parseFloat(vaultInfo.maxDepositLimit)) *
    100;

  return (
    <div className="vault-management">
      <div className="mb-4">
        <h2 className="mb-2">🏦 Vault Management</h2>
        <p className="text-muted">Manage your ETH deposits, withdrawals, and share redemptions</p>
      </div>

      {/* Vault Overview - Main Information Panel */}
      <Card className="mb-4 shadow-sm">
        <Card.Header className="bg-light">
          <div className="d-flex justify-content-between align-items-center">
            <h5 className="mb-0">📊 Vault Overview</h5>
            <Button
              variant="outline-secondary"
              size="sm"
              onClick={() => initializeVault()}
              disabled={loading}
            >
              🔄 Refresh
            </Button>
          </div>
        </Card.Header>
        <Card.Body>
          <Row className="g-4">
            <Col md={3}>
              <div className="border-end pe-3">
                <div className="text-muted small mb-1">Vault Name</div>
                <div className="h6 mb-0">{vaultInfo.name || "—"}</div>
              </div>
            </Col>
            <Col md={3}>
              <div className="border-end pe-3">
                <div className="text-muted small mb-1">Symbol</div>
                <div className="h6 mb-0">{vaultInfo.symbol || "—"}</div>
              </div>
            </Col>
            <Col md={3}>
              <div className="border-end pe-3">
                <div className="text-muted small mb-1">Status</div>
                <Badge bg={vaultInfo.active ? "success" : "danger"} className="fs-6">
                  {vaultInfo.active ? "✓ Active" : "✗ Inactive"}
                </Badge>
              </div>
            </Col>
            <Col md={3}>
              <div>
                <div className="text-muted small mb-1">Total Assets</div>
                <div className="h6 mb-0 text-primary">{vaultInfo.totalAssets || "0"} ETH</div>
              </div>
            </Col>
          </Row>

          <hr className="my-4" />

          <Row className="g-4">
            <Col md={4}>
              <div className="p-3 bg-light rounded">
                <div className="text-muted small mb-1">Total Shares</div>
                <div className="h5 mb-0">{parseFloat(vaultInfo.totalShares || 0).toLocaleString()}</div>
              </div>
            </Col>
            <Col md={4}>
              <div className="p-3 bg-light rounded">
                <div className="text-muted small mb-1">Current Deposits</div>
                <div className="h5 mb-0">{vaultInfo.currentDepositLimit || "0"} ETH</div>
              </div>
            </Col>
            <Col md={4}>
              <div className="p-3 bg-light rounded">
                <div className="text-muted small mb-1">Max Deposit Limit</div>
                <div className="h5 mb-0">{vaultInfo.maxDepositLimit || "0"} ETH</div>
              </div>
            </Col>
          </Row>

          <div className="mt-4">
            <div className="d-flex justify-content-between mb-2">
              <strong>Deposit Utilization</strong>
              <span className="text-muted">
                {vaultInfo.currentDepositLimit || "0"} / {vaultInfo.maxDepositLimit || "0"} ETH
              </span>
            </div>
            <ProgressBar
              now={depositUtilization}
              label={`${depositUtilization.toFixed(1)}%`}
              variant={depositUtilization > 80 ? "warning" : depositUtilization > 95 ? "danger" : "success"}
              className="mb-2"
              style={{ height: "24px" }}
            />
          </div>
        </Card.Body>
      </Card>

      {/* Configuration Section */}
      <Card className="mb-4 shadow-sm">
        <Card.Header className="bg-secondary text-white">
          <h5 className="mb-0">⚙️ Contract Configuration</h5>
        </Card.Header>
        <Card.Body>
          <Row className="g-3">
            <Col md={6}>
              <Form.Group>
                <Form.Label className="fw-bold">Carbon Index Contract Address</Form.Label>
                <Form.Control
                  type="text"
                  placeholder="0x..."
                  value={carbonIndexAddress}
                  onChange={(e) => {
                    setCarbonIndexAddress(e.target.value);
                    if (ethers.utils.isAddress(e.target.value)) {
                      updateCarbonIndexValue();
                    }
                  }}
                />
                <Form.Text className="text-muted">
                  Address of the CarbonIndex contract for value calculation
                </Form.Text>
              </Form.Group>
            </Col>
            <Col md={6}>
              <Form.Group>
                <Form.Label className="fw-bold">Reward Token Contract Address</Form.Label>
                <Form.Control
                  type="text"
                  placeholder="0x..."
                  value={rewardTokenAddress}
                  onChange={(e) => {
                    setRewardTokenAddress(e.target.value);
                    if (ethers.utils.isAddress(e.target.value)) {
                      updateRewardTokenBalance();
                    }
                  }}
                />
                <Form.Text className="text-muted">
                  Address of the RewardToken contract
                </Form.Text>
              </Form.Group>
            </Col>
          </Row>
        </Card.Body>
      </Card>

      {/* User Information - Personal Position */}
      <Card className="mb-4 shadow-sm">
        <Card.Header className="bg-primary text-white">
          <h5 className="mb-0">👤 Your Vault Position</h5>
        </Card.Header>
        <Card.Body>
          <Row className="g-4">
            <Col md={4}>
              <div className="p-3 border rounded">
                <div className="text-muted small mb-2">Your Vault Shares</div>
                <div className="h4 mb-0 text-primary">
                  {parseFloat(userInfo.shares || 0).toLocaleString()}
                </div>
              </div>
            </Col>
            <Col md={4}>
              <div className="p-3 border rounded">
                <div className="text-muted small mb-2">Your ETH Balance</div>
                <div className="h4 mb-0 text-success">
                  {parseFloat(userBalance || 0).toFixed(4)} ETH
                </div>
              </div>
            </Col>
            <Col md={4}>
              <div className="p-3 border rounded bg-info bg-opacity-10">
                <div className="text-muted small mb-2">
                  Vault Balance Value
                  {carbonIndexAddress && (
                    <Badge bg="info" className="ms-2">Carbon Adjusted</Badge>
                  )}
                </div>
                <div className="h4 mb-0 text-info">
                  {vaultBalanceValue || "0.000000"} ETH
                </div>
                {carbonIndexValue !== "0" && (
                  <div className="text-muted small mt-1">
                    Carbon Index: {parseFloat(carbonIndexValue).toFixed(4)}
                  </div>
                )}
              </div>
            </Col>
          </Row>

          {/* Reward Token Balance */}
          {rewardTokenAddress && (
            <>
              <hr className="my-4" />
              <Row>
                <Col md={6}>
                  <div className="p-3 bg-warning bg-opacity-10 rounded border border-warning">
                    <div className="text-muted small mb-2">Reward Token Balance</div>
                    <div className="h5 mb-0 text-warning">
                      {parseFloat(rewardTokenBalance || 0).toLocaleString()} {rewardTokenSymbol || "TOKENS"}
                    </div>
                  </div>
                </Col>
              </Row>
            </>
          )}

          <hr className="my-4" />

          <Row className="g-3">
            <Col md={4}>
              <div className="p-3 bg-light rounded text-center">
                <div className="text-muted small mb-1">Max Deposit</div>
                <div className="h6 mb-0">{userInfo.maxDeposit || "0"} ETH</div>
              </div>
            </Col>
            <Col md={4}>
              <div className="p-3 bg-light rounded text-center">
                <div className="text-muted small mb-1">Max Withdraw</div>
                <div className="h6 mb-0">{userInfo.maxWithdraw || "0"} ETH</div>
              </div>
            </Col>
            <Col md={4}>
              <div className="p-3 bg-light rounded text-center">
                <div className="text-muted small mb-1">Max Redeem</div>
                <div className="h6 mb-0">{parseFloat(userInfo.maxRedeem || 0).toLocaleString()} shares</div>
              </div>
            </Col>
          </Row>
        </Card.Body>
      </Card>

      {/* Historical Balance Value Graph */}
      {historicalData.length > 0 && (
        <Card className="mb-4 shadow-sm">
          <Card.Header className="bg-info text-white">
            <div className="d-flex justify-content-between align-items-center">
              <h5 className="mb-0">📈 Historical Balance Value (Carbon Index Adjusted)</h5>
              <Button
                variant="outline-light"
                size="sm"
                onClick={() => {
                  setHistoricalData([]);
                  localStorage.removeItem(`vaultHistory_${contracts.vault}`);
                }}
              >
                Clear History
              </Button>
            </div>
          </Card.Header>
          <Card.Body>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={historicalData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis 
                  dataKey="time" 
                  tick={{ fontSize: 12 }}
                />
                <YAxis 
                  tick={{ fontSize: 12 }}
                  label={{ value: 'Value (ETH)', angle: -90, position: 'insideLeft' }}
                />
                <Tooltip 
                  formatter={(value) => [`${parseFloat(value).toFixed(6)} ETH`, "Balance Value"]}
                  labelFormatter={(label) => `Time: ${label}`}
                />
                <Legend />
                <Line 
                  type="monotone" 
                  dataKey="value" 
                  stroke="#0d6efd" 
                  strokeWidth={2}
                  dot={{ r: 3 }}
                  name="Vault Balance Value"
                />
              </LineChart>
            </ResponsiveContainer>
            <div className="mt-3 text-center text-muted small">
              Showing last {historicalData.length} data points
            </div>
          </Card.Body>
        </Card>
      )}

      {/* Vault Operations - Transaction Panel */}
      <div className="mb-4">
        <h4 className="mb-3">Transaction Operations</h4>
        <Row className="g-4">
          {/* Deposit */}
          <Col md={4}>
            <Card className="h-100 shadow-sm border-success">
              <Card.Header className="bg-success text-white">
                <h6 className="mb-0">💰 Deposit ETH</h6>
              </Card.Header>
              <Card.Body>
                <Form.Group className="mb-3">
                  <Form.Label className="fw-bold">Amount (ETH)</Form.Label>
                  <Form.Control
                    type="number"
                    step="0.001"
                    min="0"
                    placeholder="0.1"
                    value={forms.deposit.amount}
                    onChange={(e) =>
                      handleFormChange("deposit", "amount", e.target.value)
                    }
                    className="form-control-lg"
                  />
                  <Form.Text className="text-muted d-block mt-1">
                    <small>Maximum: {userInfo.maxDeposit || "0"} ETH</small>
                  </Form.Text>
                </Form.Group>

                <Button
                  onClick={depositETH}
                  variant="success"
                  size="lg"
                  disabled={loading || !forms.deposit.amount || !vaultInfo.active}
                  className="w-100 mb-2"
                >
                  {loading ? (
                    <>
                      <span className="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
                      Processing...
                    </>
                  ) : (
                    "Deposit ETH"
                  )}
                </Button>

                <div className="alert alert-info mb-0 py-2">
                  <small>
                    <strong>Note:</strong> You'll receive vault shares proportional to your deposit
                  </small>
                </div>
              </Card.Body>
            </Card>
          </Col>

          {/* Withdraw */}
          <Col md={4}>
            <Card className="h-100 shadow-sm border-warning">
              <Card.Header className="bg-warning text-dark">
                <h6 className="mb-0">💸 Withdraw ETH</h6>
              </Card.Header>
              <Card.Body>
                <Form.Group className="mb-3">
                  <Form.Label className="fw-bold">Amount (ETH)</Form.Label>
                  <Form.Control
                    type="number"
                    step="0.001"
                    min="0"
                    placeholder="0.1"
                    value={forms.withdraw.amount}
                    onChange={(e) =>
                      handleFormChange("withdraw", "amount", e.target.value)
                    }
                    className="form-control-lg"
                  />
                  <Form.Text className="text-muted d-block mt-1">
                    <small>Maximum: {userInfo.maxWithdraw || "0"} ETH</small>
                  </Form.Text>
                </Form.Group>

                <Button
                  onClick={withdrawETH}
                  variant="warning"
                  size="lg"
                  disabled={
                    loading || !forms.withdraw.amount || !vaultInfo.active
                  }
                  className="w-100 mb-2"
                >
                  {loading ? (
                    <>
                      <span className="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
                      Processing...
                    </>
                  ) : (
                    "Withdraw ETH"
                  )}
                </Button>

                <div className="alert alert-warning mb-0 py-2">
                  <small>
                    <strong>Note:</strong> Shares will be burned proportionally to the withdrawal amount
                  </small>
                </div>
              </Card.Body>
            </Card>
          </Col>

          {/* Redeem Shares */}
          <Col md={4}>
            <Card className="h-100 shadow-sm border-info">
              <Card.Header className="bg-info text-white">
                <h6 className="mb-0">🔄 Redeem Shares</h6>
              </Card.Header>
              <Card.Body>
                <Form.Group className="mb-3">
                  <Form.Label className="fw-bold">Shares to Redeem</Form.Label>
                  <Form.Control
                    type="number"
                    step="0.001"
                    min="0"
                    placeholder="100"
                    value={forms.redeem.shares}
                    onChange={(e) =>
                      handleFormChange("redeem", "shares", e.target.value)
                    }
                    className="form-control-lg"
                  />
                  <Form.Text className="text-muted d-block mt-1">
                    <small>Maximum: {parseFloat(userInfo.maxRedeem || 0).toLocaleString()} shares</small>
                  </Form.Text>
                </Form.Group>

                <Button
                  onClick={redeemShares}
                  variant="info"
                  size="lg"
                  disabled={loading || !forms.redeem.shares || !vaultInfo.active}
                  className="w-100 mb-2"
                >
                  {loading ? (
                    <>
                      <span className="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
                      Processing...
                    </>
                  ) : (
                    "Redeem Shares"
                  )}
                </Button>

                <div className="alert alert-info mb-0 py-2">
                  <small>
                    <strong>Note:</strong> Receive ETH equivalent to your redeemed shares
                  </small>
                </div>
              </Card.Body>
            </Card>
          </Col>
        </Row>
      </div>

      {/* Help Information - Reference Guide */}
      <Card className="mb-4 shadow-sm">
        <Card.Header className="bg-light">
          <h5 className="mb-0">💡 How Vaults Work</h5>
        </Card.Header>
        <Card.Body>
          <Row className="g-4">
            <Col md={4}>
              <div className="p-3 border rounded h-100">
                <h6 className="text-primary mb-3">💰 Deposits</h6>
                <ul className="list-unstyled mb-0">
                  <li className="mb-2">
                    <strong>•</strong> Deposit ETH to receive vault shares
                  </li>
                  <li className="mb-2">
                    <strong>•</strong> Shares represent your portion of the vault
                  </li>
                  <li className="mb-0">
                    <strong>•</strong> More shares = larger portion of vault assets
                  </li>
                </ul>
              </div>
            </Col>
            <Col md={4}>
              <div className="p-3 border rounded h-100">
                <h6 className="text-warning mb-3">💸 Withdrawals</h6>
                <ul className="list-unstyled mb-0">
                  <li className="mb-2">
                    <strong>•</strong> Withdraw ETH by burning shares
                  </li>
                  <li className="mb-2">
                    <strong>•</strong> Shares burned proportionally to withdrawal
                  </li>
                  <li className="mb-0">
                    <strong>•</strong> Remaining shares maintain their value
                  </li>
                </ul>
              </div>
            </Col>
            <Col md={4}>
              <div className="p-3 border rounded h-100">
                <h6 className="text-info mb-3">🔄 Share Redemption</h6>
                <p className="mb-0 small">
                  Redeem a specific number of shares for ETH. This is useful when you want to cash out a portion of your position without calculating the exact ETH amount.
                </p>
              </div>
            </Col>
          </Row>
        </Card.Body>
      </Card>
    </div>
  );
};

export default VaultManagement;
