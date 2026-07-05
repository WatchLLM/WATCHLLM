# Glossary

## Kernel

Deterministic local enforcement core that evaluates source on the write path
and returns allow or block decisions.

## Rule

Deterministic check that evaluates source structure and returns a structured
decision with optional violations.

## Violation

A structured finding produced by a failing rule, including rule id, reason,
and optional source location evidence.

## Save Path

Execution path between an edit action and file persistence where enforcement can
intercept before disk write completion.

## Enforce Mode

Operating mode where rule failures block the write path.

## Shadow Mode

Operating mode where rule failures are recorded but do not block the write path.

## AST Node

A structural element in the parsed syntax tree representing source constructs
such as declarations, literals, calls, and imports.

## Scope

Explicit boundary of what a rule or subsystem is designed to evaluate and what
it intentionally excludes.

## Safe Function

Function or access pattern explicitly allowed by policy because it retrieves or
handles sensitive values without hardcoding them.

## Hardcoded Secret

Credential-like value embedded directly in source as a literal rather than read
from an approved secret source.

## Boundary

Declared relationship constraints defining which modules or services may import
which internal or public surfaces.

## Deterministic

Property where the same input and rule set always produce the same output.

## Local-First

Design principle requiring critical enforcement behavior to work offline without
network dependency.
