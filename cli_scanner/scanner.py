#!/usr/bin/env python3
"""
CLI Scanner for earnings-based options opportunities.
Automatically determines dates based on current time and outputs recommended tickers.
"""
 
import argparse
import logging
import sys
import re
from datetime import datetime
 
from utils.logging_utils import setup_logging
from core.scanner import EarningsScanner
 
def main():
    parser = argparse.ArgumentParser(
        description="""
        Scans for recommended options plays based on upcoming earnings.
        If run before 4PM Eastern: Checks today's post-market and tomorrow's pre-market earnings
        If run after 4PM Eastern: Checks tomorrow's post-market and following day's pre-market earnings
        """
    )
    parser.add_argument(
        '--date', '-d',
        help='Optional date to check in MM/DD/YYYY format (e.g., 03/20/2025). '
             'If not provided, uses current date logic.',
        type=str
    )
    parser.add_argument(
        '--parallel', '-p',
        help='Enable parallel processing with specified number of workers',
        type=int,
        default=0
    )
    parser.add_argument(
        '--list', '-l',
        help='Show compact output with only ticker symbols and tiers',
        action='store_true'
    )
    parser.add_argument(
        '--iron-fly', '-i',
        help='Calculate and display recommended iron fly strikes',
        action='store_true'
    )
    args = parser.parse_args()
 
    setup_logging(log_dir="logs")
    logger = logging.getLogger(__name__)
    
    input_date = None
    if args.date:
        try:
            input_date = args.date
            datetime.strptime(input_date, '%m/%d/%Y')  # Validate date format
            logger.info(f"Using provided date: {input_date}")
        except ValueError as e:
            logger.error(f"Invalid date format: {e}")
            sys.exit(1)
    else:
        now = datetime.now()
        logger.info(f"No date provided. Using current time: {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
 
    scanner = EarningsScanner()
 
    try:
        recommended, near_misses, stock_metrics = scanner.scan_earnings(
            input_date=input_date,
            workers=args.parallel
        )
        if recommended or near_misses:
            print("\n=== SCAN RESULTS ===")
            
            # Get tickers by tier
            tier1_tickers = [t for t in recommended if stock_metrics[t].get('tier', 1) == 1]
            tier2_tickers = [t for t in recommended if stock_metrics[t].get('tier', 1) == 2]
            
            # Compact output mode
            if args.list:
                print("\nTIER 1:", ", ".join(tier1_tickers) if tier1_tickers else "None")
                print("TIER 2:", ", ".join(tier2_tickers) if tier2_tickers else "None")
                print("NEAR MISSES:", ", ".join([t for t, _ in near_misses]) if near_misses else "None")
                
                # If iron fly flag is also specified
                if args.iron_fly:
                    print("\nIRON FLY RECOMMENDATIONS:")
                    # Process Tier 1 tickers
                    if tier1_tickers:
                        print("\n  TIER 1 TRADES:\n")
                        for i, ticker in enumerate(tier1_tickers):
                            if i > 0:
                                print()  # Add blank line between stocks
                            iron_fly = scanner.calculate_iron_fly_strikes(ticker)
                            if "error" not in iron_fly:
                                # Line 1: Short options and credit, Long options and debit
                                print(f"    {ticker} ({iron_fly['expiration']}):")
                                print(f"      Short ${iron_fly['short_put_strike']}P/${iron_fly['short_call_strike']}C for ${iron_fly['total_credit']} credit, "  
                                      f"Long ${iron_fly['long_put_strike']}P/${iron_fly['long_call_strike']}C for ${iron_fly['total_debit']} debit")
                                # Line 2: Break-evens and risk:reward
                                print(f"      Break-evens: ${iron_fly['lower_breakeven']}-${iron_fly['upper_breakeven']}, "  
                                      f"Risk/Reward: 1:{iron_fly['risk_reward_ratio']}")
                    # Process Tier 2 tickers
                    if tier2_tickers:
                        print("\n  TIER 2 TRADES:\n")
                        for i, ticker in enumerate(tier2_tickers):
                            if i > 0:
                                print()  # Add blank line between stocks
                            iron_fly = scanner.calculate_iron_fly_strikes(ticker)
                            if "error" not in iron_fly:
                                # Line 1: Short options and credit, Long options and debit
                                print(f"    {ticker} ({iron_fly['expiration']}):")
                                print(f"      Short ${iron_fly['short_put_strike']}P/${iron_fly['short_call_strike']}C for ${iron_fly['total_credit']} credit, "  
                                      f"Long ${iron_fly['long_put_strike']}P/${iron_fly['long_call_strike']}C for ${iron_fly['total_debit']} debit")
                                # Line 2: Break-evens and risk:reward
                                print(f"      Break-evens: ${iron_fly['lower_breakeven']}-${iron_fly['upper_breakeven']}, "  
                                      f"Risk/Reward: 1:{iron_fly['risk_reward_ratio']}")
            
            # Normal detailed output mode
            else:
                print("\nTIER 1 RECOMMENDED TRADES:")
                if tier1_tickers:
                    for ticker in tier1_tickers:
                        metrics = stock_metrics[ticker]
                        print(f"\n  {ticker}:")
                        print(f"    Price: ${metrics['price']:.2f}")
                        print(f"    Volume: {metrics['volume']:,.0f}")
                        print(f"    Winrate: {metrics['win_rate']:.1f}% over the last {metrics['win_quarters']} earnings")
                        print(f"    IV/RV Ratio: {metrics['iv_rv_ratio']:.2f}")
                        print(f"    Term Structure: {metrics['term_structure']:.3f}")
                        
                        # Calculate and display iron fly strikes if flag is set
                        if args.iron_fly:
                            iron_fly = scanner.calculate_iron_fly_strikes(ticker)
                            if "error" not in iron_fly:
                                print("    --------------------")
                                print("    IRON FLY STRATEGY:")
                                print(f"      Expiration: {iron_fly['expiration']}")
                                
                                # Line 1: Short options and premium
                                print(f"      SHORT: ${iron_fly['short_put_strike']} Put (${iron_fly['short_put_premium']}), ")
                                print(f"             ${iron_fly['short_call_strike']} Call (${iron_fly['short_call_premium']})")
                                print(f"             Total Credit: ${iron_fly['total_credit']}")
                                
                                # Line 2: Long options and premium
                                print(f"      LONG:  ${iron_fly['long_put_strike']} Put (${iron_fly['long_put_premium']}), ")
                                print(f"             ${iron_fly['long_call_strike']} Call (${iron_fly['long_call_premium']})")
                                print(f"             Total Debit: ${iron_fly['total_debit']}")
                                
                                print(f"      Net Credit: ${iron_fly['net_credit']}")
                                print(f"      Break-even Range: ${iron_fly['lower_breakeven']} to ${iron_fly['upper_breakeven']}")
                                print(f"      Wings: ${iron_fly['put_wing_width']} Put Side, ${iron_fly['call_wing_width']} Call Side")
                                print(f"      Max Profit: ${iron_fly['max_profit']}, Max Risk: ${iron_fly['max_risk']}")
                                print(f"      Risk/Reward: 1:{iron_fly['risk_reward_ratio']}")
                else:
                    print("  None")
                
                print("\nTIER 2 RECOMMENDED TRADES:")
                if tier2_tickers:
                    for ticker in tier2_tickers:
                        metrics = stock_metrics[ticker]
                        print(f"\n  {ticker}:")
                        print(f"    Price: ${metrics['price']:.2f}")
                        print(f"    Volume: {metrics['volume']:,.0f}")
                        print(f"    Winrate: {metrics['win_rate']:.1f}% over the last {metrics['win_quarters']} earnings")
                        print(f"    IV/RV Ratio: {metrics['iv_rv_ratio']:.2f}")
                        print(f"    Term Structure: {metrics['term_structure']:.3f}")
                        
                        # Calculate and display iron fly strikes if flag is set
                        if args.iron_fly:
                            iron_fly = scanner.calculate_iron_fly_strikes(ticker)
                            if "error" not in iron_fly:
                                print("    --------------------")
                                print("    IRON FLY STRATEGY:")
                                print(f"      Expiration: {iron_fly['expiration']}")
                                
                                # Line 1: Short options and premium
                                print(f"      SHORT: ${iron_fly['short_put_strike']} Put (${iron_fly['short_put_premium']}), ")
                                print(f"             ${iron_fly['short_call_strike']} Call (${iron_fly['short_call_premium']})")
                                print(f"             Total Credit: ${iron_fly['total_credit']}")
                                
                                # Line 2: Long options and premium
                                print(f"      LONG:  ${iron_fly['long_put_strike']} Put (${iron_fly['long_put_premium']}), ")
                                print(f"             ${iron_fly['long_call_strike']} Call (${iron_fly['long_call_premium']})")
                                print(f"             Total Debit: ${iron_fly['total_debit']}")
                                
                                print(f"      Net Credit: ${iron_fly['net_credit']}")
                                print(f"      Break-even Range: ${iron_fly['lower_breakeven']} to ${iron_fly['upper_breakeven']}")
                                print(f"      Wings: ${iron_fly['put_wing_width']} Put Side, ${iron_fly['call_wing_width']} Call Side")
                                print(f"      Max Profit: ${iron_fly['max_profit']}, Max Risk: ${iron_fly['max_risk']}")
                                print(f"      Risk/Reward: 1:{iron_fly['risk_reward_ratio']}")
                else:
                    print("  None")
     
                print("\nNEAR MISSES:")
                if near_misses:
                    for ticker, reason in near_misses:
                        metrics = stock_metrics[ticker]
                        print(f"\n  {ticker}:")
                        print(f"    Failed: {reason}")
                        print(f"    Metrics:")
                        print(f"      Price: ${metrics['price']:.2f}")
                        print(f"      Volume: {metrics['volume']:,.0f}")
                        print(f"      Winrate: {metrics['win_rate']:.1f}% over the last {metrics['win_quarters']} earnings")
                        print(f"      IV/RV Ratio: {metrics['iv_rv_ratio']:.2f}")
                        print(f"      Term Structure: {metrics['term_structure']:.3f}")
                else:
                    print("  None")
            
            print("\n")
        else:
            logger.info("No recommended stocks found")
    except ValueError as e:
        logger.error(f"Error: {str(e)}")
 
if __name__ == "__main__":
    main()