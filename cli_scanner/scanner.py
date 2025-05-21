#!/usr/bin/env python3
"""
CLI Scanner for earnings-based options opportunities.
Automatically determines dates based on current time and outputs recommended tickers.
"""

import argparse
import logging
import sys
import time
from datetime import datetime, timezone
from dotenv import load_dotenv
 
from utils.logging_utils import setup_logging
from core.scanner import EarningsScanner
from utils.discord_webhook import send_webhook


load_dotenv()

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
    parser.add_argument(
        '--analyze', '-a',
        help='Analyze a specific ticker symbol and display all metrics regardless of pass/fail status',
        type=str,
        metavar='TICKER'
    )
    parser.add_argument(
        '--webhook', '-w',
        help='Discord webhook URL for sending scan results',
        type=str
    )
    parser.add_argument(
        '--forever', '-fv',
        help='Repeat scan every N hours (e.g., 1 for hourly scans)',
        type=int
    )
    parser.add_argument(
        '--use-finnhub', '-f',
        help=argparse.SUPPRESS,
        action='store_true'
    )
    parser.add_argument(
        '--all-sources', '-c',
        help='Use all available earnings data sources (Investing.com, Finnhub, DoltHub)',
        action='store_true'
    )
    parser.add_argument(
        '--use-dolthub', '-u',
        help=argparse.SUPPRESS,  # Hide from help
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
        now = datetime.now(timezone.utc)
        logger.info(f'No date provided. Using current UTC time: '
                    f'{now.strftime("%Y-%m-%d %H:%M:%S %Z")}')

    scanner = EarningsScanner()
    # Check if we're analyzing a specific ticker instead of running a full scan
    if args.analyze:
        ticker = args.analyze.strip().upper()
        print(f'\n=== ANALYZING {ticker} ===\n')

        metrics = scanner.analyze_ticker(ticker)
        
        if 'error' in metrics:
            print(f"Error analyzing {ticker}: {metrics['error']}")
            return

        print(f'SPY IV/RV: {metrics.get("spy_iv_rv", 0):.2f}')
        print(f'Current thresholds - Pass: '
              f'{metrics.get("iv_rv_pass_threshold", 1.25):.2f}, '
              f'Near Miss: {metrics.get("iv_rv_near_miss_threshold", 1.0):.2f}\n')

        status = 'PASS - ' if metrics.get('pass', False) else \
                 ('NEAR MISS' if metrics.get('near_miss', False) else 'FAIL')
        if metrics.get('pass', False) and metrics.get('tier') in (1, 2):
            status += f' TIER {metrics["tier"]}'
        print(f'Status: {status}')
        print(f'Reason: {metrics.get("reason", "N/A")}\n')

        print('CORE METRICS:')
        if 'price' in metrics:
            print(f"  Price: ${metrics['price']:.2f}")
        if 'volume' in metrics:
            print(f"  Volume: {metrics['volume']:,.0f}")
        if 'term_structure' in metrics:
            print(f"  Term Structure: {metrics['term_structure']:.4f}")
        if 'iv_rv_ratio' in metrics:
            print(f"  IV/RV Ratio: {metrics['iv_rv_ratio']:.2f}")
        if 'win_rate' in metrics and 'win_quarters' in metrics:
            print(f'  Winrate: {metrics["win_rate"]:.1f}% over the last '
                  f'{metrics["win_quarters"]} earnings')

        extras = {
            k: v for k, v in metrics.items()
            if k not in ('price', 'volume', 'term_structure', 'iv_rv_ratio',
                         'win_rate', 'win_quarters', 'pass', 'near_miss',
                         'tier', 'reason', 'iv_rv_pass_threshold',
                         'iv_rv_near_miss_threshold', 'spy_iv_rv')
        }
        if extras:
            print('\nADDITIONAL METRICS:')
            for k, v in extras.items():
                if isinstance(v, float):
                    print(f'  {k}: {v:.4f}')
                else:
                    print(f'  {k}: {v}')

        if args.iron_fly:
            print("\nIRON FLY STRATEGY:")
            iron_fly = scanner.calculate_iron_fly_strikes(ticker)
            if 'error' in iron_fly:
                print(f'  {iron_fly["error"]}')
            else:
                print(f'  Expiration: {iron_fly["expiration"]}')
                print(f'  SHORT: ${iron_fly["short_put_strike"]}P/'
                      f'${iron_fly["short_call_strike"]}C for '
                      f'${iron_fly["total_credit"]} credit')
                print(f'  LONG:  ${iron_fly["long_put_strike"]}P/'
                      f'${iron_fly["long_call_strike"]}C for '
                      f'${iron_fly["total_debit"]} debit')
                print(f'  Break-evens: {iron_fly["lower_breakeven"]}-'
                      f'{iron_fly["upper_breakeven"]}, '
                      f'Risk/Reward: 1:{iron_fly["risk_reward_ratio"]}')
        return
        

    try:
        running = True
        while running:
            recommended, near_misses, stock_metrics = scanner.scan_earnings(
                input_date=input_date,
                workers=args.parallel,
                use_finnhub=args.use_finnhub,
                use_dolthub=args.use_dolthub,
                all_sources=args.all_sources
            )

            if recommended or near_misses:
                print('\n=== SCAN RESULTS ===')
                tier1 = [t for t in recommended
                         if stock_metrics[t].get('tier') == 1]
                tier2 = [t for t in recommended
                         if stock_metrics[t].get('tier') == 2]

                if args.list:
                    print('\nTIER 1:', ', '.join(tier1) or 'None')
                    print('TIER 2:', ', '.join(tier2) or 'None')
                    print('NEAR MISSES:',
                          ', '.join([t for t, _ in near_misses]) or 'None')
                else:
                    print('\nTIER 1 RECOMMENDED TRADES:')
                    if tier1:
                        for tick in tier1:
                            m = stock_metrics[tick]
                            print(f'\n  {tick}:')
                            print(f'    Price: ${m["price"]:.2f}')
                            print(f'    Volume: {m["volume"]:,.0f}')
                            print(f'    Winrate: {m["win_rate"]:.1f}% '
                                  f'over the last {m["win_quarters"]} earnings')
                            print(f'    IV/RV Ratio: {m["iv_rv_ratio"]:.2f}')
                            print(f'    Term Structure: {m["term_structure"]:.3f}')
                            if args.iron_fly:
                                fly = scanner.calculate_iron_fly_strikes(tick)
                                if 'error' not in fly:
                                    print('    --------------------')
                                    print('    IRON FLY STRATEGY:')
                                    print(f'      Expiration: '
                                          f'{fly["expiration"]}')
                                    print(f'      SHORT: '
                                          f'${fly["short_put_strike"]}P/'
                                          f'${fly["short_call_strike"]}C '
                                          f'for ${fly["total_credit"]} '
                                          'credit')
                                    print(f'      LONG:  '
                                          f'${fly["long_put_strike"]}P/'
                                          f'${fly["long_call_strike"]}C '
                                          f'for ${fly["total_debit"]} '
                                          'debit')
                                    print(f'      Break-evens: '
                                          f'{fly["lower_breakeven"]}-'
                                          f'{fly["upper_breakeven"]}, '
                                          f'Risk/Reward: '
                                          f'1:{fly["risk_reward_ratio"]}')
                    else:
                        print('  None')

                    print('\nTIER 2 RECOMMENDED TRADES:')
                    if tier2:
                        for tick in tier2:
                            m = stock_metrics[tick]
                            print(f'\n  {tick}:')
                            print(f'    Price: ${m["price"]:.2f}')
                            print(f'    Volume: {m["volume"]:,.0f}')
                            print(f'    Winrate: {m["win_rate"]:.1f}% '
                                  f'over the last {m["win_quarters"]} earnings')
                            print(f'    IV/RV Ratio: {m["iv_rv_ratio"]:.2f}')
                            print(f'    Term Structure: {m["term_structure"]:.3f}')
                            if args.iron_fly:
                                fly = scanner.calculate_iron_fly_strikes(tick)
                                if 'error' not in fly:
                                    print('    --------------------')
                                    print('    IRON FLY STRATEGY:')
                                    print(f'      Expiration: '
                                          f'{fly["expiration"]}')
                                    print(f'      SHORT: '
                                          f'${fly["short_put_strike"]}P/'
                                          f'${fly["short_call_strike"]}C '
                                          f'for ${fly["total_credit"]} '
                                          'credit')
                                    print(f'      LONG:  '
                                          f'${fly["long_put_strike"]}P/'
                                          f'${fly["long_call_strike"]}C '
                                          f'for ${fly["total_debit"]} '
                                          'debit')
                                    print(f'      Break-evens: '
                                          f'{fly["lower_breakeven"]}-'
                                          f'{fly["upper_breakeven"]}, '
                                          f'Risk/Reward: '
                                          f'1:{fly["risk_reward_ratio"]}')
                    else:
                        print('  None')

                    print('\nNEAR MISSES:')
                    if near_misses:
                        for tick, reason in near_misses:
                            m = stock_metrics[tick]
                            print(f'\n  {tick}:')
                            print(f'    Failed: {reason}')
                            print('    Metrics:')
                            print(f'      Price: ${m["price"]:.2f}')
                            print(f'      Volume: {m["volume"]:,.0f}')
                            print(f'      Winrate: {m["win_rate"]:.1f}% '
                                  f'over the last {m["win_quarters"]} earnings')
                            print(f'      IV/RV Ratio: {m["iv_rv_ratio"]:.2f}')
                            print(f'      Term Structure: {m["term_structure"]:.3f}')
                    else:
                        print('  None')

                if args.webhook:
                    # build a list of Embed fields
                    fields = []

                    # Tier 1 details
                    if tier1:
                        for tick in tier1:
                            m = stock_metrics[tick]
                            name = f"Tier 1 — {tick}"
                            value_lines = [
                                f"• Price: `${m['price']:.2f}`",
                                f"• Volume: `{m['volume']:,.0f}`",
                                f"• Winrate: `{m['win_rate']:.1f}%` over last `{m['win_quarters']}` earnings",
                                f"• IV/RV Ratio: `{m['iv_rv_ratio']:.2f}`",
                                f"• Term Structure: `{m['term_structure']:.3f}`",
                                f"• Tier: `{m.get('tier')}`"
                            ]
                            # iron fly
                            if args.iron_fly:
                                fly = scanner.calculate_iron_fly_strikes(tick)
                                if 'error' not in fly:
                                    value_lines.extend([
                                        "",
                                        "**Iron Fly**:",
                                        f"▫️ Expiration: `{fly['expiration']}`",
                                        f"▫️ Short: `{fly['short_put_strike']}P / {fly['short_call_strike']}C` for `{fly['total_credit']}` credit",
                                        f"▫️ Long: `{fly['long_put_strike']}P / {fly['long_call_strike']}C` for `{fly['total_debit']}` debit",
                                        f"▫️ Break-evens: `{fly['lower_breakeven']} – {fly['upper_breakeven']}`",
                                        f"▫️ Risk/Reward: `1:{fly['risk_reward_ratio']}`"
                                    ])
                            fields.append({'name': name, 'value': "\n".join(value_lines), 'inline': False})

                    # Tier 2 details
                    if tier2:
                        for tick in tier2:
                            m = stock_metrics[tick]
                            name = f"Tier 2 — {tick}"
                            value_lines = [
                                f"• Price: `${m['price']:.2f}`",
                                f"• Volume: `{m['volume']:,.0f}`",
                                f"• Winrate: `{m['win_rate']:.1f}%` over last `{m['win_quarters']}` earnings",
                                f"• IV/RV Ratio: `{m['iv_rv_ratio']:.2f}`",
                                f"• Term Structure: `{m['term_structure']:.3f}`",
                                f"• Tier: `{m.get('tier')}`"
                            ]
                            if args.iron_fly:
                                fly = scanner.calculate_iron_fly_strikes(tick)
                                if 'error' not in fly:
                                    value_lines.extend([
                                        "",
                                        "**Iron Fly**:",
                                        f"▫️ Expiration: `{fly['expiration']}`",
                                        f"▫️ Short: `{fly['short_put_strike']}P / {fly['short_call_strike']}C` for `{fly['total_credit']}` credit",
                                        f"▫️ Long: `{fly['long_put_strike']}P / {fly['long_call_strike']}C` for `{fly['total_debit']}` debit",
                                        f"▫️ Break-evens: `{fly['lower_breakeven']} – {fly['upper_breakeven']}`",
                                        f"▫️ Risk/Reward: `1:{fly['risk_reward_ratio']}`"
                                    ])
                            fields.append({'name': name, 'value': "\n".join(value_lines), 'inline': False})

                    # Near misses
                    if near_misses:
                        for tick, reason in near_misses:
                            m = stock_metrics[tick]
                            name = f"Near Miss — {tick}"
                            value = (
                                f"• Failed: `{reason}`\n"
                                f"• Price: `${m['price']:.2f}`\n"
                                f"• Volume: `{m['volume']:,.0f}`\n"
                                f"• Winrate: `{m['win_rate']:.1f}%` over last `{m['win_quarters']}` earnings\n"
                                f"• IV/RV Ratio: `{m['iv_rv_ratio']:.2f}`\n"
                                f"• Term Structure: `{m['term_structure']:.3f}`"
                            )
                            fields.append({'name': name, 'value': value, 'inline': False})

                    # fallback if nothing to show
                    if not fields:
                        fields.append({'name': 'No recommendations', 'value': 'None found', 'inline': False})

                    embed = {
                        'title': 'Earnings Scanner Results',
                        'color': 3066993,
                        'fields': fields,
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    }
                    send_webhook(args.webhook, embed, logger)
            
            else:
                logger.info('No recommended stocks found')

            if args.forever and args.forever > 0:
                logger.info(f'Sleeping for {args.forever} hours...')
                time.sleep(args.forever * 3600)
            else:
                running = False

    except KeyboardInterrupt:
        logger.info('Interrupted; exiting.')
    except ValueError as e:
        logger.error(f'Error: {e}')

if __name__ == '__main__':
    main()
