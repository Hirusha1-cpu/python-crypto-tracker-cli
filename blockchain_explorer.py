import os
import json
import requests
from datetime import datetime
from typing import Optional, Dict, List
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class BlockchainExplorer:
    """A CLI tool to explore blockchain data using Etherscan API"""
    
    def __init__(self):
        self.api_key = os.getenv('ETHERSCAN_API_KEY')
        if not self.api_key:
            raise ValueError("ETHERSCAN_API_KEY not found in environment variables")
        self.base_url = "https://api.etherscan.io/v2/api"
    
    def get_balance(self, address: str) -> Dict:
        """Get ETH balance for a wallet address"""
        params = {
            'chainid': 11155111,
            'module': 'account',
            'action': 'balance',
            'address': address,
            'tag': 'latest',
            'apikey': self.api_key
        }
        
        response = requests.get(self.base_url, params=params)
        data = response.json()
        
        if data['status'] == '1':
            balance_wei = int(data['result'])
            balance_eth = balance_wei / 10**18
            return {
                'address': address,
                'balance_wei': balance_wei,
                'balance_eth': balance_eth,
                'balance_usd': None  # Will be filled if we add price feed.
            }
        else:
            raise Exception(f"API Error: {data.get('message', 'Unknown error')}")
    
    def get_transactions(self, address: str, page: int = 1, offset: int = 10) -> Dict:
        """Get transaction history for a wallet address"""
        params = {
            'chainid': 11155111,
            'module': 'account',
            'action': 'txlist',
            'address': address,
            'startblock': 0,
            'endblock': 99999999,
            'page': page,
            'offset': offset,
            'sort': 'desc',
            'apikey': self.api_key
        }
        
        response = requests.get(self.base_url, params=params)
        data = response.json()
        
        if data['status'] == '1':
            transactions = []
            for tx in data['result']:
                transactions.append({
                    'hash': tx['hash'],
                    'from': tx['from'],
                    'to': tx['to'],
                    'value': float(tx['value']) / 10**18,
                    'gas_price': float(tx['gasPrice']) / 10**9,  # Gwei
                    'gas_used': int(tx['gasUsed']),
                    'timestamp': datetime.fromtimestamp(int(tx['timeStamp'])).strftime('%Y-%m-%d %H:%M:%S'),
                    'status': 'Success' if tx['txreceipt_status'] == '1' else 'Failed'
                })
            
            return {
                'address': address,
                'transactions': transactions,
                'total': len(transactions)
            }
        else:
            raise Exception(f"API Error: {data.get('message', 'Unknown error')}")
    
    def get_gas_price(self) -> Dict:
        """Get current gas price information"""
        params = {
            'chainid': 1,
            'module': 'gastracker',
            'action': 'gasoracle',
            'apikey': self.api_key
        }
        
        response = requests.get(self.base_url, params=params)
        data = response.json()
        
        if data['status'] == '1':
            result = data['result']
            return {
                'safe_gas_price': float(result['SafeGasPrice']),
                'propose_gas_price': float(result['ProposeGasPrice']),
                'fast_gas_price': float(result['FastGasPrice']),
                'last_block': int(result['LastBlock']),
                'suggested_base_fee': float(result['suggestBaseFee'])
            }
        else:
            raise Exception(f"API Error: {data.get('message', 'Unknown error')}")
    
    def display_balance(self, balance_data: Dict):
        """Display balance information in a formatted way"""
        print("\n" + "="*60)
        print(f"💰 BALANCE INFORMATION")
        print("="*60)
        print(f"Address: {balance_data['address']}")
        print(f"Balance: {balance_data['balance_eth']:.6f} ETH")
        print(f"Balance: {balance_data['balance_wei']:,} WEI")
        print("="*60)
    
    def display_transactions(self, tx_data: Dict):
        """Display transaction history in a formatted way"""
        print("\n" + "="*60)
        print(f"📊 TRANSACTION HISTORY")
        print("="*60)
        print(f"Address: {tx_data['address']}")
        print(f"Total transactions: {tx_data['total']}")
        print("-"*60)
        
        for i, tx in enumerate(tx_data['transactions'], 1):
            print(f"\nTransaction #{i}")
            print(f"  Hash: {tx['hash'][:10]}...{tx['hash'][-8:]}")
            print(f"  From: {tx['from'][:10]}...{tx['from'][-8:]}")
            print(f"  To:   {tx['to'][:10]}...{tx['to'][-8:]}")
            print(f"  Value: {tx['value']:.6f} ETH")
            print(f"  Gas Price: {tx['gas_price']:.2f} Gwei")
            print(f"  Gas Used: {tx['gas_used']:,}")
            print(f"  Time: {tx['timestamp']}")
            print(f"  Status: {tx['status']}")
            print("-"*60)
    
    def display_gas_price(self, gas_data: Dict):
        """Display gas price information in a formatted way"""
        print("\n" + "="*60)
        print(f"⛽ GAS PRICE INFORMATION")
        print("="*60)
        print(f"Safe (Low):    {gas_data['safe_gas_price']:.1f} Gwei")
        print(f"Proposed (Avg): {gas_data['propose_gas_price']:.1f} Gwei")
        print(f"Fast (High):   {gas_data['fast_gas_price']:.1f} Gwei")
        print(f"Base Fee:      {gas_data['suggested_base_fee']:.1f} Gwei")
        print(f"Last Block:    {gas_data['last_block']:,}")
        print("="*60)

class CLI:
    """Command Line Interface for Blockchain Explorer"""
    
    def __init__(self):
        self.explorer = BlockchainExplorer()
        self.running = True
    
    def clear_screen(self):
        """Clear the terminal screen"""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def show_menu(self):
        """Display the main menu"""
        print("\n" + "="*60)
        print("🚀 BLOCKCHAIN EXPLORER CLI")
        print("="*60)
        print("1. Check Wallet Balance")
        print("2. View Transaction History")
        print("3. Check Gas Price")
        print("4. Full Wallet Report")
        print("5. Exit")
        print("="*60)
    
    def get_address(self) -> str:
        """Get wallet address from user"""
        address = input("\nEnter Ethereum wallet address: ").strip()
        if not address:
            print("❌ Address cannot be empty!")
            return None
        return address
    
    def run(self):
        """Main CLI loop"""
        while self.running:
            self.show_menu()
            choice = input("\nSelect an option (1-5): ").strip()
            
            if choice == '1':
                self.check_balance()
            elif choice == '2':
                self.view_transactions()
            elif choice == '3':
                self.check_gas_price()
            elif choice == '4':
                self.full_report()
            elif choice == '5':
                print("\n👋 Goodbye!")
                self.running = False
            else:
                print("\n❌ Invalid option. Please try again.")
            
            if self.running:
                input("\nPress Enter to continue...")
                self.clear_screen()
    
    def check_balance(self):
        """Handle balance check"""
        address = self.get_address()
        if address:
            try:
                balance = self.explorer.get_balance(address)
                self.explorer.display_balance(balance)
            except Exception as e:
                print(f"\n❌ Error: {str(e)}")
    
    def view_transactions(self):
        """Handle transaction view"""
        address = self.get_address()
        if address:
            try:
                page = input("Enter page number (default: 1): ").strip()
                page = int(page) if page else 1
                
                offset = input("Enter transactions per page (default: 10): ").strip()
                offset = int(offset) if offset else 10
                
                transactions = self.explorer.get_transactions(address, page, offset)
                self.explorer.display_transactions(transactions)
            except Exception as e:
                print(f"\n❌ Error: {str(e)}")
    
    def check_gas_price(self):
        """Handle gas price check"""
        try:
            gas_data = self.explorer.get_gas_price()
            self.explorer.display_gas_price(gas_data)
        except Exception as e:
            print(f"\n❌ Error: {str(e)}")
    
    def full_report(self):
        """Generate a full wallet report"""
        address = self.get_address()
        if address:
            try:
                print("\n📊 Generating full wallet report...")
                
                # Get balance
                balance = self.explorer.get_balance(address)
                self.explorer.display_balance(balance)
                
                # Get gas price
                gas_data = self.explorer.get_gas_price()
                self.explorer.display_gas_price(gas_data)
                
                # Get transactions
                transactions = self.explorer.get_transactions(address, 1, 5)
                self.explorer.display_transactions(transactions)
                
                print("\n✅ Full report generated successfully!")
                
            except Exception as e:
                print(f"\n❌ Error: {str(e)}")

def main():
    """Main entry point"""
    try:
        cli = CLI()
        cli.run()
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")

if __name__ == "__main__":
    main()