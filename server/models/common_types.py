# soap-web-services/server/models/common_types.py
from __future__ import annotations # VERY FIRST LINE

from typing import Literal

# Policy Status Literals
PolicyStatusSendRegOutput = Literal["1", "2", "3"]
PolicyStatusGetStatusOutput = Literal["1", "2", "3", "4", "5"]
PolicyStatusStornoOutput = PolicyStatusGetStatusOutput # Or define specifically if different

# Claim Status Literal
ClaimStatusOutput = Literal["1", "2", "3", "4"] # 1: Pending, 2: Closed, 3: Rejected, 4: Paid

# Storno Type Literal
StornoType = Literal["Storno", "Cancellation"]

# Claim Type Literal (as defined in the PDF for SendClaim InputData.XMLData <Type>)
ClaimType = Literal[
    "DEATH_ACC", "DEATH_NAT", "DISABILITY",
    "HOSPITALIZATION_ACC", "HOSPITALIZATION_ILL",
    "INCAPACITY_ACC", "INCAPACITY_ILL"
]

# Add any other simple, shared Literal types or TypeAliases here.
