# TODO List for Fixed Stake Strategy Implementation

## Completed Tasks
- [x] Add `create_fixed_stake_strategy` static method to StrategyBuilder in `auto_trader.py`
- [x] Modify stake calculation logic in `start_auto_trading` to use fixed stake when strategy type is 'fixed_stake'
- [x] Integrate risk management checks for fixed stake trades

## Pending Tasks
- [ ] Test the new fixed stake strategy by running auto trading with the fixed stake config
- [ ] Verify integration with existing risk checks (max stake, drawdown, etc.)
- [ ] Update frontend components to support selecting fixed stake strategy
- [ ] Add validation for fixed_stake_amount in strategy config
- [ ] Document the new strategy in project documentation

## Notes
- The fixed stake strategy uses a constant stake amount regardless of AI confidence
- Risk management checks are still applied to ensure stake doesn't exceed limits
- Default fixed stake amount is 1.0 USD, configurable via strategy config
