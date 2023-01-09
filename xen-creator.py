import time
from web3 import Web3
import json
import requests
from pycoingecko import CoinGeckoAPI


## ----------- CONFIG START ----------- ##

# Set the XENFT parameters
vmu = 128 # How many VMUs to mint?
manual_max_term = 440  # Hardcoded max term for your XENFT

# if TRUE script will automatically return max term and overwrite above manual_max_term value.
# If FALSE, script will default to manually configured value (manual_max_term)
use_automatic_max_term = True

# Set gas-related claiming parameters
only_claim_if_gas_is_below = 15
max_priority_fee_per_gas = 1

# Claim/Mint parameters
claim_when_consecutive_count = 3 # if n checks in a row are at below OnlyClaimIfGasBelow, only then claim it
how_many_seconds_between_checks = 10

# Infura URL. Note: All requests to Infura must have a valid API key appended to the request URL or they will fail.
# Get your own at: https://infura.io (Video Guide: https://youtu.be/R2WkpF4Em7k)
infura_url = "https://mainnet.infura.io/v3/ABCDEF # Replace ABCDEF with your Infura API id
# Connect to the Ethereum network using Infura using WEB3 (DON'T TOUCH)
web3 = Web3(Web3.HTTPProvider(infura_url))

# Replace these with your own wallet details
your_wallet_address = '0x' # account from which we'll pay for XENFT (ensure you have sufficient funds)
your_wallet_address_private_key = '012345abcdef...' # private key of your wallet address

# XENFT & XEN smart contract addresses (DON'T TOUCH)
xenft_contract_address = web3.toChecksumAddress('0x0a252663dbcc0b073063d6420a40319e438cfa59')
xen_public_address = web3.toChecksumAddress('0x06450dEe7FD2Fb8E39061434BAbCFC05599a6Fb8')

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
    # Create a session with the infura API
    session = requests.Session()
    session.headers.update({'Content-Type':'application/json'})

    # Infura connection URL
    connection_url = infura_url

    # Request the gas price from the API
    gas_price_data = session.post(url=connection_url, json={"jsonrpc":"2.0","method":"eth_gasPrice","params":[],"id":1})

    # Parse the response and get the price in gwei
    gas_price_gwei = int(gas_price_data.json()['result'], 16) / 1000000000

    # Calculate low, medium, and high gas prices

    medium_gas_price_gwei = gas_price_gwei
    return round(medium_gas_price_gwei, 2)

## ----------- FUNCTIONS END ----------- ##




## ----------- BODY OF THE PROGRAM - START (DON'T TOUCH) ----------- ##

if use_automatic_max_term:
    term = fetch_current_max_term(xen_public_address) # This will fetch the current MAX TERM automatically from XEN smart contract.
else:
    term = manual_max_term

print(f"XENFT CONFIGURATION: VMU: {vmu}, TERM: {term}, Max Gwei: {only_claim_if_gas_is_below}")

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
        print(f"Waiting for gas price to drop to {only_claim_if_gas_is_below}. The current gas price: {maxFeePerGas}")
        time.sleep(how_many_seconds_between_checks)
    else:
        consecutive_count += 1
        print(f"Test {consecutive_count} of {claim_when_consecutive_count} - Gas is below {only_claim_if_gas_is_below}  gwei ({maxFeePerGas})")
        if consecutive_count == claim_when_consecutive_count:
            # Once gas at acceptable range, move ahead with transactions
            print(f"Ready to claim, the gas price was below {only_claim_if_gas_is_below} gwei for {claim_when_consecutive_count} consecutive times!")
            break
        else:
            time.sleep(how_many_seconds_between_checks)

eth_cost_in_usd = get_eth_usd_value()
balance_before_claim = round(float(web3.fromWei(web3.eth.getBalance(your_wallet_address), 'ether')),6)
total_account_value = round(eth_cost_in_usd*balance_before_claim,2)
print(f"Account balance before XENFT claim: {balance_before_claim} ETH (${total_account_value})")

# Build the transaction
tx = contract.functions.bulkClaimRank(vmu, term).buildTransaction({
    'from': your_wallet_address,
    'nonce': web3.eth.getTransactionCount(web3.toChecksumAddress(your_wallet_address)),
    'maxFeePerGas': web3.toWei(maxFeePerGas, 'gwei'),
    'maxPriorityFeePerGas': web3.toWei(max_priority_fee_per_gas, 'gwei')
})
gas = web3.eth.estimateGas(tx)
tx['gas'] = gas


# Estimate Cost
gas_price = web3.toWei(maxFeePerGas, 'gwei')
cost = gas * gas_price
cost_in_ether = float(round(web3.fromWei(cost, 'ether'),6))
total_cost_in_usd = round(cost_in_ether * eth_cost_in_usd,2)
per_vmu_cost = round(total_cost_in_usd/vmu,2)
print(f"Current ETH value: ${eth_cost_in_usd}")
print(f"Expected XENFT Cost: {cost_in_ether} ETH (${total_cost_in_usd}) or ${per_vmu_cost}/VMU.")

# Sign the transaction with your private key
signed_tx = web3.eth.account.signTransaction(tx, your_wallet_address_private_key)

# Send the transaction to XENFT Smart Contract
tx_hash = web3.eth.sendRawTransaction(signed_tx.rawTransaction)

# Print transaction hash URL
print(f"XENFT (vmu:{vmu}, term:{term}) - Successfully Initiated at {maxFeePerGas} gwei. URL: https://etherscan.io/tx/" + str(web3.toHex(tx_hash)))

# Wait for the transaction to be mined
tx_receipt = web3.eth.waitForTransactionReceipt(tx_hash)

test_count = 0
while web3.eth.getBalance(your_wallet_address) == balance_before_claim:
    test_count = test_count + 1
    print(f"Waiting for the transaction to be processed! Test: #{test_count}")
    time.sleep(how_many_seconds_between_checks)

balance_after_claim = round(float(web3.fromWei(web3.eth.getBalance(your_wallet_address), 'ether')),6)

print(f"XENFT (vmu:{vmu}, term:{term}) - Successfully Created at {maxFeePerGas} gwei. URL: https://etherscan.io/tx/" + str(web3.toHex(tx_hash)))
total_cost = float(round(balance_before_claim - balance_after_claim, 4))
total_cost_in_usd = round((total_cost * eth_cost_in_usd),2)
per_vmu_cost = round(total_cost_in_usd/vmu, 2)
print(f"Actual XENFT Cost: {total_cost} ETH (${total_cost_in_usd}) or ${per_vmu_cost}/VMU. Current ETH value: ${eth_cost_in_usd}")
print("-----------------------------------")

## ----------- BODY OF THE PROGRAM - END ----------- ##
