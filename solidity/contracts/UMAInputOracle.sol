// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";

/**
 * @dev UMA OOV3 minimal interface (top-level)
 */
interface OptimisticOracleV3Interface {
    function defaultIdentifier() external view returns (bytes32);

    function assertTruth(
        bytes memory claim,
        address asserter,
        address callbackRecipient,
        address escalationManager,
        uint64 liveness,
        IERC20 currency,
        uint256 bond,
        bytes32 identifier,
        bytes32 domain
    ) external returns (bytes32 assertionId);

    function settleAssertion(bytes32 assertionId) external returns (bool assertedTruthfully);
}

/**
 * @title UMA Optimistic Oracle V3 Data-Asserter-style Input Oracle
 * @notice Integrates UMA OOV3 to assert and settle arbitrary off-chain data on-chain.
 *         Mirrors the Data Asserter tutorial flow from UMA docs, adapted to expose
 *         latest(dataId) reads for downstream contracts.
 *
 * References:
 * - UMA OOV3 Data Asserter: https://docs.uma.xyz/developers/optimistic-oracle-v3/data-asserter
 */
contract UMAInputOracle is Ownable {
    // ----------------------------
    // Storage
    // ----------------------------
    IERC20 public defaultCurrency;                // Bond currency
    OptimisticOracleV3Interface public oo;        // UMA OOV3 instance
    bytes32 public defaultIdentifier;             // Price identifier used for assertions

    // Global parameters (can be tuned by owner)
    uint64 public assertionLiveness;              // Challenge window in seconds
    uint256 public bond;                          // Bond amount in `defaultCurrency`
    bytes32 public domain;                        // Optional domain separation for claims

    // Data assertion object as in UMA example
    struct DataAssertion {
        bytes32 dataId;        // Unique identifier of the data
        bytes32 data;          // Bytes32-encoded value asserted
        address asserter;      // Address credited at resolution
        bool resolved;         // Whether settled
        bool truthfully;       // Whether resolved as truthful
    }

    // assertionId => DataAssertion
    mapping(bytes32 => DataAssertion) public assertionsData;

    // dataId => latest assertionId
    mapping(bytes32 => bytes32) public latestAssertionByDataId;

    // Optionally track last resolved value per dataId for quick reads
    mapping(bytes32 => bytes32) public resolvedDataById;

    // ----------------------------
    // Events
    // ----------------------------
    event AssertionCreated(
        bytes32 indexed dataId,
        bytes32 indexed assertionId,
        address indexed asserter,
        bytes32 data,
        uint64 liveness,
        uint256 bond
    );

    event AssertionResolved(
        bytes32 indexed dataId,
        bytes32 indexed assertionId,
        bool assertedTruthfully,
        bytes32 data
    );

    event ConfigUpdated(
        address defaultCurrency,
        address oo,
        uint64 assertionLiveness,
        uint256 bond,
        bytes32 defaultIdentifier,
        bytes32 domain
    );

    // ----------------------------
    // Constructor
    // ----------------------------
    constructor(address _defaultCurrency, address _optimisticOracleV3) {
        require(_defaultCurrency != address(0), "invalid currency");
        require(_optimisticOracleV3 != address(0), "invalid oracle");

        defaultCurrency = IERC20(_defaultCurrency);
        oo = OptimisticOracleV3Interface(_optimisticOracleV3);
        defaultIdentifier = oo.defaultIdentifier();

        // Sensible defaults (owner can update later)
        assertionLiveness = 2 hours;
        bond = 0; // In many tutorial/test environments default bond may be 0
        domain = bytes32(0);

        emit ConfigUpdated(_defaultCurrency, _optimisticOracleV3, assertionLiveness, bond, defaultIdentifier, domain);
    }

    // ----------------------------
    // Admin configuration
    // ----------------------------
    function setAssertionLiveness(uint64 newLiveness) external onlyOwner {
        assertionLiveness = newLiveness;
        emit ConfigUpdated(address(defaultCurrency), address(oo), assertionLiveness, bond, defaultIdentifier, domain);
    }

    function setBond(uint256 newBond) external onlyOwner {
        bond = newBond;
        emit ConfigUpdated(address(defaultCurrency), address(oo), assertionLiveness, bond, defaultIdentifier, domain);
    }

    function setDomain(bytes32 newDomain) external onlyOwner {
        domain = newDomain;
        emit ConfigUpdated(address(defaultCurrency), address(oo), assertionLiveness, bond, defaultIdentifier, domain);
    }

    function setDefaultCurrency(address newCurrency) external onlyOwner {
        require(newCurrency != address(0), "invalid currency");
        defaultCurrency = IERC20(newCurrency);
        emit ConfigUpdated(address(defaultCurrency), address(oo), assertionLiveness, bond, defaultIdentifier, domain);
    }

    function setOracle(address newOO) external onlyOwner {
        require(newOO != address(0), "invalid oracle");
        oo = OptimisticOracleV3Interface(newOO);
        defaultIdentifier = oo.defaultIdentifier();
        emit ConfigUpdated(address(defaultCurrency), address(oo), assertionLiveness, bond, defaultIdentifier, domain);
    }

    // ----------------------------
    // Assertion flow (Data Asserter pattern)
    // ----------------------------

    /**
     * @notice Assert that `data` is the correct value for `dataId`.
     *         Pulls `bond` from caller, approves OO, and calls assertTruth.
     * @dev Callers must have approved this contract to transfer `bond` amount if bond>0.
     */
    function assertDataFor(bytes32 dataId, bytes32 data, address asserter) external returns (bytes32 assertionId) {
        // Pull bond into this contract then approve OO (if bond > 0)
        if (bond > 0) {
            require(defaultCurrency.transferFrom(msg.sender, address(this), bond), "bond transfer failed");
            require(defaultCurrency.approve(address(oo), bond), "approve failed");
        }

        // Build human-readable claim bytes as in UMA example (not used on-chain beyond dispute text)
        bytes memory claim = abi.encodePacked(
            "Data asserted: 0x",
            _toHex(data),
            " for dataId: 0x",
            _toHex(dataId),
            " and asserter: 0x",
            _toHexAddress(asserter),
            " at timestamp: ",
            _uintToUtf8(block.timestamp),
            " in UMAInputOracle at 0x",
            _toHexAddress(address(this)),
            " is valid."
        );

        assertionId = oo.assertTruth(
            claim,
            asserter,
            address(this),          // callback recipient
            address(0),             // no escalation manager
            assertionLiveness,
            defaultCurrency,
            bond,
            defaultIdentifier,
            domain
        );

        assertionsData[assertionId] = DataAssertion({
            dataId: dataId,
            data: data,
            asserter: asserter,
            resolved: false,
            truthfully: false
        });

        latestAssertionByDataId[dataId] = assertionId;

        emit AssertionCreated(dataId, assertionId, asserter, data, assertionLiveness, bond);
    }

    /**
     * @notice Convenience: settle an assertion after liveness window passes.
     *         Anyone can call; OO enforces liveness.
     */
    function settle(bytes32 assertionId) external returns (bool assertedTruthfully) {
        assertedTruthfully = oo.settleAssertion(assertionId);
        // The resolution callback below finalizes storage updates
    }

    // ----------------------------
    // UMA OOV3 Callbacks
    // ----------------------------

    /**
     * @notice Called by OOV3 on assertion settlement.
     */
    function assertionResolvedCallback(bytes32 assertionId, bool assertedTruthfully) external {
        require(msg.sender == address(oo), "only OO");
        DataAssertion storage da = assertionsData[assertionId];
        // Ignore unknown assertion IDs to avoid reverting OO
        if (da.asserter == address(0)) return;

        da.resolved = true;
        da.truthfully = assertedTruthfully;

        if (assertedTruthfully) {
            resolvedDataById[da.dataId] = da.data;
        }

        emit AssertionResolved(da.dataId, assertionId, assertedTruthfully, da.data);
    }

    /**
     * @notice Optional: called by OOV3 when an assertion is disputed.
     *         No-op here, but provided for completeness.
     */
    function assertionDisputedCallback(bytes32 /*assertionId*/) external view {
        require(msg.sender == address(oo), "only OO");
    }

    // ----------------------------
    // Read APIs
    // ----------------------------

    /**
     * @notice Returns latest assertion info for a given dataId.
     */
    function latest(bytes32 dataId) external view returns (
        bool isResolved,
        bool truthfully,
        bytes32 data,
        bytes32 assertionId
    ) {
        assertionId = latestAssertionByDataId[dataId];
        DataAssertion memory da = assertionsData[assertionId];
        return (da.resolved, da.truthfully, da.data, assertionId);
    }

    /**
     * @notice Return resolved data (if any) for a dataId. Zero if none or not truthful.
     */
    function latestResolved(bytes32 dataId) external view returns (bytes32) {
        return resolvedDataById[dataId];
    }

    // ----------------------------
    // Helpers (string/bytes formatting)
    // ----------------------------

    function _toHex(bytes32 data) internal pure returns (bytes memory) {
        bytes16 hexSymbols = 0x30313233343536373839616263646566; // 0-9a-f
        bytes memory str = new bytes(64);
        for (uint256 i = 0; i < 32; i++) {
            uint8 b = uint8(data[i]);
            str[2 * i] = bytes1(hexSymbols[b >> 4]);
            str[2 * i + 1] = bytes1(hexSymbols[b & 0x0f]);
        }
        return str;
    }

    function _toHexAddress(address account) internal pure returns (bytes memory) {
        return _toHex(bytes32(uint256(uint160(account))));
    }

    function _uintToUtf8(uint256 v) internal pure returns (bytes memory) {
        if (v == 0) return "0";
        uint256 j = v;
        uint256 len;
        while (j != 0) {
            len++;
            j /= 10;
        }
        bytes memory bstr = new bytes(len);
        uint256 k = len;
        j = v;
        while (j != 0) {
            k = k - 1;
            uint8 temp = uint8(48 + (j % 10));
            bstr[k] = bytes1(temp);
            j /= 10;
        }
        return bstr;
    }
}
