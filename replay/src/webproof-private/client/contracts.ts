export type SourceFreshness={state:'live'|'stale'|'snapshot';stale:boolean;refreshedAt:number|null};
export type ProofSummary={id:string;sessionId:string;url:string;targetDomain:string;path:string;observedAt:number;status:string;source:SourceFreshness;verificationMode:'commitment_only';attestation:false;proofType:'local_merkle_stub';proofVersion:string;chain:'base-sepolia'|'base-mainnet';l2TransactionHash:string|null;confirmations:number;requiredConfirmations:number};
export type LadderRow={level:number;sibling:string;siblingSide:'left'|'right';computedParent:string};
export type ProofDetail=ProofSummary&{responseHash:string;rawProof:string|null;disclaimer:string;merkle:{leafHash:string;leafIndex:number;root:string;path:string[];valid:boolean;computedRoot:string;ladder:LadderRow[]}};
export type ProofListResponse={proofs:ProofSummary[];pagination:{page:number;pageSize:number;total:number;totalPages:number}};
