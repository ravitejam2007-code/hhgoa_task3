// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title EvidenceRegistry
 * @notice Anchors cryptographic SHA-256 fingerprints of reverse-image evidence
 *         on-chain for tamper-evident provenance verification.
 * @dev Stores only cryptographic hashes and provenance URLs; never raw face images or embeddings.
 */
contract EvidenceRegistry {

    struct Evidence {
        bytes32 evidenceHash;
        string sourceUrl;
        string searchProvider;
        uint256 createdAt;
        address submitter;
    }

    // Auto-incrementing numeric evidence ID starting at 1
    uint256 private _nextEvidenceId = 1;

    // Mapping from numeric evidence ID to Evidence record
    mapping(uint256 => Evidence) private _records;

    /**
     * @notice Emitted when a new evidence fingerprint is anchored to the blockchain.
     */
    event EvidenceRecorded(
        uint256 indexed evidenceId,
        bytes32 indexed evidenceHash,
        string sourceUrl,
        string searchProvider,
        address indexed submitter
    );

    /**
     * @notice Record a new evidence fingerprint.
     * @param evidenceHash 32-byte SHA-256 digest of canonical evidence JSON.
     * @param sourceUrl The discovered source or social media URL.
     * @param searchProvider Name of the search provider that discovered the match.
     * @return evidenceId Unique identifier for the recorded evidence.
     */
    function recordEvidence(
        bytes32 evidenceHash,
        string calldata sourceUrl,
        string calldata searchProvider
    ) external returns (uint256) {
        require(evidenceHash != bytes32(0), "Evidence hash cannot be zero");

        uint256 evidenceId = _nextEvidenceId;
        _nextEvidenceId++;

        _records[evidenceId] = Evidence({
            evidenceHash: evidenceHash,
            sourceUrl: sourceUrl,
            searchProvider: searchProvider,
            createdAt: block.timestamp,
            submitter: msg.sender
        });

        emit EvidenceRecorded(
            evidenceId,
            evidenceHash,
            sourceUrl,
            searchProvider,
            msg.sender
        );

        return evidenceId;
    }

    /**
     * @notice Retrieve an evidence record by ID.
     * @param evidenceId The numeric evidence ID.
     */
    function getEvidence(
        uint256 evidenceId
    )
        external
        view
        returns (
            bytes32 evidenceHash,
            string memory sourceUrl,
            string memory searchProvider,
            uint256 createdAt,
            address submitter
        )
    {
        Evidence storage record = _records[evidenceId];
        require(record.createdAt != 0, "Evidence record not found");

        return (
            record.evidenceHash,
            record.sourceUrl,
            record.searchProvider,
            record.createdAt,
            record.submitter
        );
    }

    /**
     * @notice Verify whether a given evidence hash matches the on-chain record.
     * @param evidenceId The numeric evidence ID.
     * @param evidenceHash The 32-byte evidence hash to verify.
     * @return True if the hash matches the on-chain record, false otherwise.
     */
    function verifyEvidence(
        uint256 evidenceId,
        bytes32 evidenceHash
    ) external view returns (bool) {
        Evidence storage record = _records[evidenceId];
        if (record.createdAt == 0) {
            return false;
        }
        return record.evidenceHash == evidenceHash;
    }

    /**
     * @notice Returns total number of evidence records created.
     */
    function totalEvidence() external view returns (uint256) {
        return _nextEvidenceId - 1;
    }
}
