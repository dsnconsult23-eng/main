from typing import Dict, Any, Optional, List
from models.policy import Policy
from models.claim import Claim

class PolicyRepository:
    """In-memory repository for insurance policies"""
    
    def __init__(self):
        self._storage: Dict[str, Policy] = {}

    def create(self, policy: Policy) -> Policy:
        """Store a new policy"""
        if policy.gacid in self._storage:
            raise ValueError(f"Policy with GACID {policy.gacid} already exists")
        self._storage[policy.gacid] = policy
        return policy

    def get(self, gacid: str) -> Optional[Policy]:
        """Retrieve a policy by GACID"""
        return self._storage.get(gacid)

    def update(self, policy: Policy) -> Policy:
        """Update an existing policy"""
        if policy.gacid not in self._storage:
            raise ValueError(f"Policy with GACID {policy.gacid} not found")
        self._storage[policy.gacid] = policy
        return policy

    def delete(self, gacid: str) -> None:
        """Delete a policy by GACID"""
        if gacid in self._storage:
            del self._storage[gacid]

    def list_all(self) -> List[Policy]:
        """List all stored policies"""
        return list(self._storage.values())

class ClaimRepository:
    """In-memory repository for insurance claims"""
    
    def __init__(self):
        self._storage: Dict[str, Claim] = {}
        self._policy_claims: Dict[str, List[str]] = {}  # policy_gacid -> list of claim_ids

    def create(self, claim: Claim) -> Claim:
        """Store a new claim"""
        if claim.gac_claim_id in self._storage:
            raise ValueError(f"Claim with ID {claim.gac_claim_id} already exists")
        
        self._storage[claim.gac_claim_id] = claim
        
        # Maintain policy->claims relationship
        if claim.policy_number not in self._policy_claims:
            self._policy_claims[claim.policy_number] = []
        self._policy_claims[claim.policy_number].append(claim.gac_claim_id)
        
        return claim

    def get(self, gac_claim_id: str) -> Optional[Claim]:
        """Retrieve a claim by ID"""
        return self._storage.get(gac_claim_id)

    def get_by_policy(self, policy_number: str) -> List[Claim]:
        """Retrieve all claims for a policy"""
        claim_ids = self._policy_claims.get(policy_number, [])
        return [self._storage[claim_id] for claim_id in claim_ids]

    def update(self, claim: Claim) -> Claim:
        """Update an existing claim"""
        if claim.gac_claim_id not in self._storage:
            raise ValueError(f"Claim with ID {claim.gac_claim_id} not found")
        self._storage[claim.gac_claim_id] = claim
        return claim

    def delete(self, gac_claim_id: str) -> None:
        """Delete a claim by ID"""
        if gac_claim_id in self._storage:
            claim = self._storage[gac_claim_id]
            del self._storage[gac_claim_id]
            
            # Remove from policy->claims relationship
            if claim.policy_number in self._policy_claims:
                self._policy_claims[claim.policy_number].remove(gac_claim_id)

# Make repositories available when importing from package
__all__ = ['PolicyRepository', 'ClaimRepository']