import time
import json
import datetime
import requests
from web3 import Web3
import getpass
from pycoingecko import CoinGeckoAPI

# DISCLAIMER:
# You are solely responsible for ensuring the secure configuration and operation of this script, including but not limited to protecting it from unauthorized access by third parties.
# Failure to do so may result in the loss of your private keys, XENFTs or other cryptocurrencies stored in your account. You should exercise caution and only run this script on a secure workstation or server.
# By using this script, you acknowledge that you understand the inherent risks associated with running this script and that you agree to use this script at your own risk.
# The creator of this script will not be held liable for any damages, loss of funds, or other negative consequences that may result from you or any third party using this script.
# You are solely responsible for any actions taken using this script, and for securing your private keys and other sensitive information.
# This script is provided 'as is,' and the creator makes no warranty, express or implied, of any kind.


## ----------- CONFIG START ----------- ##

# Set the XENFT parameters
vmu = 128 # How many VMUs to mint?
manual_max_term = 443  # Hardcoded max term for your XENFT

# if TRUE script will automatically return max term and overwrite above manual_max_term value.
# If FALSE, script will default to manually configured value (manual_max_term)
use_automatic_max_term = True

# Set gas-related claiming parameters
only_claim_if_gas_is_below = 13
max_priority_fee_per_gas = 1.1

# Claim/Mint parameters
claim_when_consecutive_count = 3  # if n checks in a row are at below OnlyClaimIfGasBelow, only then claim it
how_many_seconds_between_checks = 10

# For RPC node you can use Infura URL. Note: All requests to Infura must have a valid API key appended to the request URL or they will fail.
# Get your own at: https://infura.io (Video Guide: https://youtu.be/R2WkpF4Em7k)
rpc_url = "https://mainnet.infura.io/v3/ABCDEF" # Replace ABCDEF with your Infura API id
# Alternatively, if you don't want to sign up with Infura and monitor your own requests, just uncomment the line below to use Public Ethereum RPC, or get one from: https://llamanodes.com/public-rpc
# rpc_url = "https://eth.llamarpc.com"

# Connect to the Ethereum network through RPC using WEB3 (DON'T TOUCH)
web3 = Web3(Web3.HTTPProvider(rpc_url))

# Replace these with your own wallet details
your_wallet_address = '0x' # replace with the account from which we'll pay for XENFT (ensure you have sufficient funds)

# PRIVATE KEYS
# RECOMMENDED APPROACH: Script will ask you to enter the private key manually (at runtime)
your_wallet_address_private_key = getpass.getpass(prompt="Please enter your wallet private key: ")
# NOT SECURE & NOT RECOMMENDED: Uncomment the following line to hardcode your wallet's private key
# your_wallet_address_private_key = '012345abcdef...'

# XENFT & XEN smart contract addresses (DON'T TOUCH)
xenft_contract_address = web3.toChecksumAddress('0x0a252663dbcc0b073063d6420a40319e438cfa59')
xen_public_address = web3.toChecksumAddress('0x06450dEe7FD2Fb8E39061434BAbCFC05599a6Fb8')

# Time Format
now = datetime.datetime.now()
time_format = f"{now.year}-{now.month:02}-{now.day:02} {now.hour:02}:{now.minute:02}:{now.second:02}"

## ------------ CONFIG END ------------ ##



## ----------- FUNCTIONS START (DON'T TOUCH) ----------- ##

# Get Ethereum cost in USD
def get_eth_usd_value():
    cg = CoinGeckoAPI()
    price = cg.get_price(ids=['ethereum'], vs_currencies='usd')
    usd_value = price['ethereum']['usd']
    return usd_value

def fetch_abi(address):
    response = requests.get(f'https://api.etherscan.io/api?module=contract&action=getabi&address={address}')
    return json.dumps(json.loads(response.json()['result']))


def fetch_current_max_term(xen_address):
    address = web3.toChecksumAddress(xen_address)
    xen_abi = fetch_abi(address)
    xen_contract = web3.eth.contract(address=address, abi=xen_abi)
    current_max_term = int(xen_contract.functions.getCurrentMaxTerm().call() / (60*60*24))
    #print(f"Setting the XEN maximum term to: {current_max_term}")
    return current_max_term


def get_gas_price():
    # Create a session with the RPC API
    session = requests.Session()
    session.headers.update({'Content-Type':'application/json'})

    # RPC connection URL
    connection_url = rpc_url

    # Request the gas price from the API
    gas_price_data = session.post(url=connection_url, json={"jsonrpc":"2.0","method":"eth_gasPrice","params":[],"id":1})

    # Parse the response and get the price in gwei
    gas_price_gwei = int(gas_price_data.json()['result'], 16) / 1000000000

    # Calculate low, medium, and high gas prices

    medium_gas_price_gwei = gas_price_gwei * 1.1  # low gwei price + 10%
    return round(medium_gas_price_gwei, 2)

## ----------- FUNCTIONS END ----------- ##




## ----------- BODY OF THE PROGRAM - START (DON'T TOUCH) ----------- ##

if use_automatic_max_term:
    term = fetch_current_max_term(xen_public_address) # This will fetch the current MAX TERM automatically from XEN smart contract.
else:
    term = manual_max_term
print("------------------------------------------ XENFT CONFIGURATION ------------------------------------------")
print(f"VMU: {vmu}, TERM: {term}, Max Gas Fee (gwei): {only_claim_if_gas_is_below}, Max Priority Fee (gwei) : {max_priority_fee_per_gas}, Auto retrieve Max Term: {use_automatic_max_term}")
print(f"Auto-claim XENFT when gas drops below {only_claim_if_gas_is_below} gwei for {claim_when_consecutive_count} consecutive checks, performed at {how_many_seconds_between_checks} second intervals.")
print("---------------------------------------------------------------------------------------------------------")

# Retrieve XENFT ABI from the smart contract
time.sleep(how_many_seconds_between_checks)
xenft_abi = fetch_abi(xenft_contract_address)

# Connect to the contract
contract = web3.eth.contract(address=xenft_contract_address, abi=xenft_abi)

# Wait for the Ethereum network gas to drop to your minimum acceptable value
consecutive_count = 0
while True:
    maxFeePerGas = get_gas_price()
    if maxFeePerGas > only_claim_if_gas_is_below:
        consecutive_count = 0
        now = datetime.datetime.now()
        print(f"{time_format} - Waiting for gas price to drop to {only_claim_if_gas_is_below}. The current gas price: {maxFeePerGas}")
        time.sleep(how_many_seconds_between_checks)
    else:
        consecutive_count += 1
        now = datetime.datetime.now()
        print(f"{time_format} - Test {consecutive_count} of {claim_when_consecutive_count} - Gas is below {only_claim_if_gas_is_below}  gwei ({maxFeePerGas})")
        if consecutive_count == claim_when_consecutive_count:
            # Once gas at acceptable range, move ahead with transactions
            print(f"Ready to claim, the gas price is below {only_claim_if_gas_is_below} gwei for {claim_when_consecutive_count} consecutive times!")
            break
        else:
            time.sleep(how_many_seconds_between_checks)

eth_cost_in_usd = get_eth_usd_value()
balance_before_claim = round(float(web3.fromWei(web3.eth.getBalance(your_wallet_address), 'ether')),6)
total_account_value = round(eth_cost_in_usd*balance_before_claim,2)
print(f"Account balance before XENFT claim: {balance_before_claim} ETH (${total_account_value})")


# Build the transaction
try:
    tx = contract.functions.bulkClaimRank(vmu, term).buildTransaction({
        'from': your_wallet_address,
        'nonce': web3.eth.getTransactionCount(web3.toChecksumAddress(your_wallet_address)),
        'maxFeePerGas': web3.toWei(maxFeePerGas, 'gwei'),
        'maxPriorityFeePerGas': web3.toWei(max_priority_fee_per_gas, 'gwei')
    })
    gas = web3.eth.estimateGas(tx)
    tx['gas'] = gas
    print("Transaction built successfully!")

    if web3.eth.getBalance(your_wallet_address) < gas*maxFeePerGas:
        raise Exception("Not enough Ether in your wallet address to pay for the transaction")

    # Estimate Cost
    gas_price = web3.toWei(maxFeePerGas, 'gwei')
    cost = gas * gas_price
    cost_in_ether = float(round(web3.fromWei(cost, 'ether'),6))
    total_cost_in_usd = round(cost_in_ether * eth_cost_in_usd,2)
    per_vmu_cost = round(total_cost_in_usd/vmu,2)
    print(f"{time_format} - Current ETH value: ${eth_cost_in_usd}")
    print(f"{time_format} - Expected XENFT Cost: {cost_in_ether} ETH (${total_cost_in_usd}) or ${per_vmu_cost}/VMU.")

    # Sign the transaction with your private key
    signed_tx = web3.eth.account.signTransaction(tx, your_wallet_address_private_key)

    # Send the transaction to XENFT Smart Contract
    tx_hash = web3.eth.sendRawTransaction(signed_tx.rawTransaction)

    # Print transaction hash URL
    print(f"{time_format} - XENFT (vmu:{vmu}, term:{term}) - Successfully Initiated at {maxFeePerGas} gwei. URL: https://etherscan.io/tx/" + str(web3.toHex(tx_hash)))

    # Wait for the transaction to be mined
    # tx_receipt = web3.eth.waitForTransactionReceipt(tx_hash)

    test_count = 0
    while round(float(web3.fromWei(web3.eth.getBalance(your_wallet_address), 'ether')),6) == balance_before_claim:
        test_count = test_count + 1
        now = datetime.datetime.now()
        print(f"{time_format} - Waiting for the transaction to be processed! Test: #{test_count}")
        time.sleep(how_many_seconds_between_checks+20)

    balance_after_claim = round(float(web3.fromWei(web3.eth.getBalance(your_wallet_address), 'ether')),6)
    now = datetime.datetime.now()
    print(f"{time_format} - XENFT (vmu:{vmu}, term:{term}) - Successfully Created at {maxFeePerGas} gwei. URL: https://etherscan.io/tx/" + str(web3.toHex(tx_hash)))
    total_cost = float(round(balance_before_claim - balance_after_claim, 4))
    total_cost_in_usd = round((total_cost * eth_cost_in_usd),2)
    per_vmu_cost = round(total_cost_in_usd/vmu, 2)
    print(f"Actual (final) XENFT Cost: {total_cost} ETH (${total_cost_in_usd}) or ${per_vmu_cost}/VMU. Calculated based on ETH value: ${eth_cost_in_usd} as of {time_format}")
    print("-----------------------------------")

    ## ----------- BODY OF THE PROGRAM - END ----------- ##

except Exception as e:
    print(f"An error occurred: {e}")