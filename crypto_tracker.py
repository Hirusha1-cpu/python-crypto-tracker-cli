import asyncio
import aiohttp
import json
import time
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass
from colorama import init, Fore, Style

# Initialize colorama for colored output
init(autoreset=True)

@dataclass
class CryptoPrice:
    """Data class for cryptocurrency price information"""
    symbol: str
    name: str
    price_usd: float
    price_btc: float
    market_cap: float
    volume_24h: float
    price_change_24h: float
    high_24h: float
    low_24h: float
    last_updated: str
    
    def __str__(self):
        change_color = Fore.GREEN if self.price_change_24h >= 0 else Fore.RED
        return (
            f"{Fore.CYAN}{self.symbol}{Style.RESET_ALL} ({self.name})\n"
            f"  Price: ${self.price_usd:,.2f}\n"
            f"  Change (24h): {change_color}{self.price_change_24h:+.2f}%{Style.RESET_ALL}\n"
            f"  Market Cap: ${self.market_cap:,.0f}\n"
            f"  24h Volume: ${self.volume_24h:,.0f}\n"
            f"  24h High: ${self.high_24h:,.2f}\n"
            f"  24h Low: ${self.low_24h:,.2f}\n"
            f"  Updated: {self.last_updated}"
        )

class CryptoPriceTracker:
    """Async cryptocurrency price tracker using CoinGecko API"""
    
    def __init__(self):
        self.base_url = "https://api.coingecko.com/api/v3"
        self.session = None
        self.cache = {}
        self.cache_duration = 60  # Cache duration in seconds
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def get_price(self, coin_id: str, vs_currency: str = 'usd') -> Optional[CryptoPrice]:
        """Get current price for a single cryptocurrency"""
        # Check cache
        cache_key = f"{coin_id}_{vs_currency}"
        if cache_key in self.cache:
            cached_data, timestamp = self.cache[cache_key]
            if time.time() - timestamp < self.cache_duration:
                return cached_data
        
        try:
            params = {
                'ids': coin_id,
                'vs_currencies': vs_currency,
                'include_market_cap': 'true',
                'include_24hr_vol': 'true',
                'include_24hr_change': 'true',
                'include_last_updated_at': 'true'
            }
            
            async with self.session.get(
                f"{self.base_url}/simple/price",
                params=params
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    if coin_id in data:
                        coin_data = data[coin_id]
                        price = CryptoPrice(
                            symbol=coin_id.upper(),
                            name=coin_id.title(),
                            price_usd=coin_data.get(vs_currency, 0),
                            price_btc=0,  # Will be filled separately if needed
                            market_cap=coin_data.get(f'{vs_currency}_market_cap', 0),
                            volume_24h=coin_data.get(f'{vs_currency}_24h_vol', 0),
                            price_change_24h=coin_data.get(f'{vs_currency}_24h_change', 0),
                            high_24h=0,  # Not available in simple price endpoint
                            low_24h=0,   # Not available in simple price endpoint
                            last_updated=datetime.fromtimestamp(
                                coin_data.get('last_updated_at', time.time())
                            ).strftime('%Y-%m-%d %H:%M:%S')
                        )
                        
                        # Cache the result
                        self.cache[cache_key] = (price, time.time())
                        return price
                
                return None
                
        except Exception as e:
            print(f"Error fetching price for {coin_id}: {str(e)}")
            return None
    
    async def get_multiple_prices(self, coin_ids: List[str], vs_currency: str = 'usd') -> Dict[str, Optional[CryptoPrice]]:
        """Get prices for multiple cryptocurrencies"""
        results = {}
        tasks = [self.get_price(coin_id, vs_currency) for coin_id in coin_ids]
        prices = await asyncio.gather(*tasks)
        
        for coin_id, price in zip(coin_ids, prices):
            results[coin_id] = price
        
        return results
    
    async def get_market_data(self, coin_id: str) -> Optional[Dict]:
        """Get detailed market data for a cryptocurrency"""
        try:
            async with self.session.get(
                f"{self.base_url}/coins/{coin_id}"
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    market_data = data.get('market_data', {})
                    return {
                        'name': data.get('name', coin_id.title()),
                        'symbol': data.get('symbol', coin_id).upper(),
                        'current_price': market_data.get('current_price', {}).get('usd', 0),
                        'market_cap': market_data.get('market_cap', {}).get('usd', 0),
                        'total_volume': market_data.get('total_volume', {}).get('usd', 0),
                        'high_24h': market_data.get('high_24h', {}).get('usd', 0),
                        'low_24h': market_data.get('low_24h', {}).get('usd', 0),
                        'price_change_24h': market_data.get('price_change_percentage_24h', 0),
                        'ath': market_data.get('ath', {}).get('usd', 0),
                        'atl': market_data.get('atl', {}).get('usd', 0),
                        'last_updated': data.get('last_updated', datetime.now().isoformat())
                    }
                return None
        except Exception as e:
            print(f"Error fetching market data for {coin_id}: {str(e)}")
            return None
    
    async def get_trending(self) -> List[Dict]:
        """Get trending cryptocurrencies"""
        try:
            async with self.session.get(
                f"{self.base_url}/search/trending"
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    trending = []
                    for item in data.get('coins', []):
                        coin = item.get('item', {})
                        trending.append({
                            'name': coin.get('name', 'Unknown'),
                            'symbol': coin.get('symbol', 'Unknown'),
                            'market_cap_rank': coin.get('market_cap_rank'),
                            'price_btc': coin.get('price_btc', 0)
                        })
                    return trending
                return []
        except Exception as e:
            print(f"Error fetching trending: {str(e)}")
            return []

class Dashboard:
    """Interactive dashboard for crypto price tracking"""
    
    def __init__(self):
        self.tracker = CryptoPriceTracker()
        self.running = True
    
    def clear_screen(self):
        """Clear the terminal screen"""
        import os
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def display_header(self):
        """Display dashboard header"""
        print(f"\n{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}🚀 CRYPTO PRICE TRACKER DASHBOARD{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
        print(f"Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{Fore.CYAN}{'-'*60}{Style.RESET_ALL}")
    
    def display_price(self, price: CryptoPrice):
        """Display price information for a single cryptocurrency"""
        if price:
            print(f"\n{str(price)}")
        else:
            print(f"\n{Fore.RED}❌ Price data not available{Style.RESET_ALL}")
    
    def display_market_data(self, data: Dict):
        """Display detailed market data"""
        if data:
            print(f"\n{Fore.MAGENTA}📊 DETAILED MARKET DATA{Style.RESET_ALL}")
            print(f"{Fore.CYAN}{'-'*40}{Style.RESET_ALL}")
            print(f"Name: {data['name']} ({data['symbol']})")
            print(f"Current Price: ${data['current_price']:,.2f}")
            print(f"Market Cap: ${data['market_cap']:,.0f}")
            print(f"24h Volume: ${data['total_volume']:,.0f}")
            print(f"24h High: ${data['high_24h']:,.2f}")
            print(f"24h Low: ${data['low_24h']:,.2f}")
            change_color = Fore.GREEN if data['price_change_24h'] >= 0 else Fore.RED
            print(f"24h Change: {change_color}{data['price_change_24h']:+.2f}%{Style.RESET_ALL}")
            print(f"ATH: ${data['ath']:,.2f}")
            print(f"ATL: ${data['atl']:,.2f}")
            print(f"Last Updated: {data['last_updated']}")
    
    def display_trending(self, trending: List[Dict]):
        """Display trending cryptocurrencies"""
        if trending:
            print(f"\n{Fore.GREEN}🔥 TRENDING CRYPTOCURRENCIES{Style.RESET_ALL}")
            print(f"{Fore.CYAN}{'-'*40}{Style.RESET_ALL}")
            for i, coin in enumerate(trending[:5], 1):
                print(f"{i}. {coin['name']} ({coin['symbol']}) - Rank: {coin['market_cap_rank']}")
    
    async def run(self):
        """Main dashboard loop"""
        async with self.tracker:
            while self.running:
                self.clear_screen()
                self.display_header()
                
                print("\nOptions:")
                print("1. Check single crypto price")
                print("2. Check multiple crypto prices")
                print("3. View detailed market data")
                print("4. View trending cryptocurrencies")
                print("5. Auto-refresh dashboard")
                print("6. Exit")
                
                choice = input("\nSelect an option (1-6): ").strip()
                
                if choice == '1':
                    await self.single_price()
                elif choice == '2':
                    await self.multiple_prices()
                elif choice == '3':
                    await self.detailed_data()
                elif choice == '4':
                    await self.view_trending()
                elif choice == '5':
                    await self.auto_refresh()
                elif choice == '6':
                    print(f"\n{Fore.YELLOW}👋 Goodbye!{Style.RESET_ALL}")
                    self.running = False
                else:
                    print(f"\n{Fore.RED}❌ Invalid option{Style.RESET_ALL}")
                
                if self.running:
                    input(f"\n{Fore.CYAN}Press Enter to continue...{Style.RESET_ALL}")
    
    async def single_price(self):
        """Check single cryptocurrency price"""
        coin_id = input("Enter cryptocurrency ID (e.g., bitcoin, ethereum): ").strip().lower()
        if coin_id:
            price = await self.tracker.get_price(coin_id)
            self.display_price(price)
    
    async def multiple_prices(self):
        """Check multiple cryptocurrency prices"""
        coin_ids = input("Enter cryptocurrency IDs (comma-separated): ").strip().lower()
        if coin_ids:
            coin_list = [c.strip() for c in coin_ids.split(',')]
            prices = await self.tracker.get_multiple_prices(coin_list)
            
            print(f"\n{Fore.MAGENTA}📊 MULTIPLE CRYPTO PRICES{Style.RESET_ALL}")
            print(f"{Fore.CYAN}{'-'*40}{Style.RESET_ALL}")
            for coin_id, price in prices.items():
                if price:
                    print(f"\n{str(price)}")
                    print(f"{Fore.CYAN}{'-'*40}{Style.RESET_ALL}")
                else:
                    print(f"\n{Fore.RED}❌ No data for {coin_id}{Style.RESET_ALL}")
    
    async def detailed_data(self):
        """View detailed market data"""
        coin_id = input("Enter cryptocurrency ID: ").strip().lower()
        if coin_id:
            data = await self.tracker.get_market_data(coin_id)
            self.display_market_data(data)
    
    async def view_trending(self):
        """View trending cryptocurrencies"""
        trending = await self.tracker.get_trending()
        self.display_trending(trending)
    
    async def auto_refresh(self):
        """Auto-refresh dashboard with multiple cryptocurrencies"""
        coin_ids = input("Enter cryptocurrency IDs (comma-separated): ").strip().lower()
        if not coin_ids:
            return
        
        coin_list = [c.strip() for c in coin_ids.split(',')]
        refresh_interval = input("Enter refresh interval (seconds, default: 10): ").strip()
        refresh_interval = int(refresh_interval) if refresh_interval else 10
        
        print(f"\n{Fore.GREEN}Starting auto-refresh every {refresh_interval} seconds...{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Press Ctrl+C to stop{Style.RESET_ALL}")
        
        try:
            while True:
                self.clear_screen()
                self.display_header()
                
                print(f"\n{Fore.MAGENTA}📊 AUTO-REFRESH DASHBOARD{Style.RESET_ALL}")
                print(f"{Fore.CYAN}{'-'*40}{Style.RESET_ALL}")
                print(f"Refreshing every {refresh_interval} seconds")
                print(f"Press Ctrl+C to stop\n")
                
                prices = await self.tracker.get_multiple_prices(coin_list)
                for coin_id, price in prices.items():
                    if price:
                        print(f"\n{str(price)}")
                        print(f"{Fore.CYAN}{'-'*40}{Style.RESET_ALL}")
                    else:
                        print(f"\n{Fore.RED}❌ No data for {coin_id}{Style.RESET_ALL}")
                
                await asyncio.sleep(refresh_interval)
                
        except KeyboardInterrupt:
            print(f"\n\n{Fore.YELLOW}Stopped auto-refresh{Style.RESET_ALL}")
            await asyncio.sleep(1)

async def main():
    """Main entry point"""
    try:
        dashboard = Dashboard()
        await dashboard.run()
    except KeyboardInterrupt:
        print(f"\n\n{Fore.YELLOW}👋 Goodbye!{Style.RESET_ALL}")
    except Exception as e:
        print(f"\n{Fore.RED}❌ Error: {str(e)}{Style.RESET_ALL}")

if __name__ == "__main__":
    asyncio.run(main())