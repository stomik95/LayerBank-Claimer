#!/usr/bin/env python3

from web3 import Web3
from eth_account import Account
import time
import random
import os

class Colors:
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    END = '\033[0m'

def colored_print(text, color=Colors.WHITE):
    print(f"{color}{text}{Colors.END}")

LINEA_RPC = "https://rpc.linea.build"
LAYERBANK_USDC = "0x2aD69A0Cf272B9941c7dDcaDa7B0273E9046C4B0"
LAYERBANK_WSTETH = "0xE33520c74bac3c537BfEEe0F65e80471F3d564b9"
LAYERBANK_CONTRACT = "0x009a0b7C38B542208936F1179151CD08E2943833"

# Настройки задержек (в секундах)
DELAY_BETWEEN_WALLETS = (30, 60)  # Рандомная задержка между кошельками (мин, макс)
DELAY_BETWEEN_ACTIONS = (5, 15)   # Рандомная задержка между действиями (мин, макс)
DELAY_AFTER_TRANSACTION = (3, 10) # Рандомная задержка после транзакции (мин, макс)

SHUFFLE_WALLETS = True  # True = рандомный порядок, False = последовательный порядок

BALANCE_ABI = [{"inputs": [{"name": "_owner", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "balance", "type": "uint256"}], "type": "function"}]

LAYERBANK_ABI = [
    {"inputs": [], "name": "claimLab", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
    {"inputs": [{"internalType": "address", "name": "gToken", "type": "address"}, {"internalType": "uint256", "name": "gAmount", "type": "uint256"}], "name": "redeemToken", "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}], "stateMutability": "nonpayable", "type": "function"},
    {"inputs": [{"internalType": "address", "name": "gToken", "type": "address"}, {"internalType": "uint256", "name": "uAmount", "type": "uint256"}], "name": "redeemUnderlying", "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}], "stateMutability": "nonpayable", "type": "function"}
]

def random_delay(delay_range):
    delay = random.uniform(delay_range[0], delay_range[1])
    colored_print(f"⏳ Ожидание {delay:.1f} секунд...", Colors.YELLOW)
    time.sleep(delay)

def safe_redeem(w3, account, layerbank_contract, gToken, gAmount, nonce, token_name):
    try:
        print(f"   💸 Выводим {gAmount / 10**18} gToken {token_name}...")
        
        redeem_tx = layerbank_contract.functions.redeemToken(
            gToken, gAmount
        ).build_transaction({
            'from': account.address,
            'gas': 500000,
            'gasPrice': w3.eth.gas_price,
            'nonce': nonce,
        })
        
        signed_tx = account.sign_transaction(redeem_tx)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        colored_print(f"   ✅ Транзакция отправлена: https://lineascan.build/tx/{tx_hash.hex()}", Colors.GREEN)
        
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        if receipt.status == 1:
            colored_print(f"   🎉 {token_name} успешно выведен!", Colors.GREEN)
            return True
        else:
            colored_print(f"   ❌ Транзакция вывода {token_name} не удалась", Colors.RED)
            return False
            
    except Exception as e:
        print(f"   ❌ Ошибка при выводе {token_name}: {e}")
        return False

def get_wallet_address(private_key):
    try:
        account = Account.from_key(private_key)
        return account.address
    except Exception as e:
        print(f"Ошибка получения адреса из приватного ключа: {e}")
        return None

def check_and_process_wallet(w3, private_key):
    wallet_address = get_wallet_address(private_key)
    if not wallet_address:
        return
    
    colored_print(f"\n{wallet_address}", Colors.BLUE)
    
    usdc_contract = w3.eth.contract(address=LAYERBANK_USDC, abi=BALANCE_ABI)
    wsteth_contract = w3.eth.contract(address=LAYERBANK_WSTETH, abi=BALANCE_ABI)
    
    usdc_gbalance = usdc_contract.functions.balanceOf(wallet_address).call()
    wsteth_gbalance = wsteth_contract.functions.balanceOf(wallet_address).call()
    
    print(f"📊 Балансы LayerBank токенов:")
    print(f"   💵 USDC: {usdc_gbalance / 10**18}")
    print(f"   🔷 wstETH: {wsteth_gbalance / 10**18}")
    
    layerbank_contract = w3.eth.contract(address=LAYERBANK_CONTRACT, abi=LAYERBANK_ABI)
    
    active_markets = []
    if usdc_gbalance > 0:
        active_markets.append(f"USDC ({usdc_gbalance / 10**18})")
    if wsteth_gbalance > 0:
        active_markets.append(f"wstETH ({wsteth_gbalance / 10**18})")
    
    if active_markets:
        print(f"✅ Активные позиции: {', '.join(active_markets)}")
    
    if usdc_gbalance > 0 or wsteth_gbalance > 0:
        if usdc_gbalance > 0:
            print(f"   💵 USDC: redeemToken(gAmount={usdc_gbalance})")
        if wsteth_gbalance > 0:
            print(f"   🔷 wstETH: redeemToken(gAmount={wsteth_gbalance})")
        
        print(f"\n🚀 Начинаем вывод средств...")
        
        account = Account.from_key(private_key)
        
        nonce = w3.eth.get_transaction_count(wallet_address)
        
        try:
            print(f"\n🎁 Шаг 1: Клеймим награды LAB...")
            claim_tx = layerbank_contract.functions.claimLab().build_transaction({
                'from': wallet_address,
                'gas': 200000,
                'gasPrice': w3.eth.gas_price,
                'nonce': nonce,
            })
            
            signed_tx = account.sign_transaction(claim_tx)
            tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            colored_print(f"   ✅ Клейм отправлен: https://lineascan.build/tx/{tx_hash.hex()}", Colors.GREEN)
            
            w3.eth.wait_for_transaction_receipt(tx_hash)
            nonce += 1
            
            random_delay(DELAY_AFTER_TRANSACTION)
            
            if usdc_gbalance > 0:
                print(f"\n💵 Шаг 2: Выводим USDC...")
                success = safe_redeem(w3, account, layerbank_contract, LAYERBANK_USDC, usdc_gbalance, nonce, "USDC")
                if success:
                    nonce += 1
                    random_delay(DELAY_BETWEEN_ACTIONS)
            
            if wsteth_gbalance > 0:
                print(f"\n🔷 Шаг 3: Выводим wstETH...")
                success = safe_redeem(w3, account, layerbank_contract, LAYERBANK_WSTETH, wsteth_gbalance, nonce, "wstETH")
                if success:
                    random_delay(DELAY_AFTER_TRANSACTION)
            
            print(f"\n🎉 Все операции завершены успешно!")
            
        except Exception as e:
            print(f"\n❌ Ошибка при выполнении операций: {e}")
    else:
        print(f"\n💤 Средств для вывода не обнаружено")

def main():
    colored_print("🚀 LayerBank Auto-Claim & Redeem Bot", Colors.CYAN + Colors.BOLD)
    colored_print("=" * 50, Colors.CYAN)
    
    w3 = Web3(Web3.HTTPProvider(LINEA_RPC))
    status_color = Colors.GREEN if w3.is_connected() else Colors.RED
    colored_print(f"🌐 Подключение к Linea: {'✔' if w3.is_connected() else '×'}", status_color)
    
    with open("wallets.txt", "r") as f:
        private_keys = [line.strip() for line in f if line.strip()]
    
    if SHUFFLE_WALLETS:
        random.shuffle(private_keys)
    
    colored_print(f"📋 Найдено кошельков: {len(private_keys)}", Colors.PURPLE)
    colored_print(f"⏰ Задержки: между кошельками {DELAY_BETWEEN_WALLETS[0]}-{DELAY_BETWEEN_WALLETS[1]}с, между действиями {DELAY_BETWEEN_ACTIONS[0]}-{DELAY_BETWEEN_ACTIONS[1]}с", Colors.YELLOW)
    colored_print(f"🔄 Режим обработки: {'Рандомный' if SHUFFLE_WALLETS else 'Последовательный'}", Colors.CYAN)
    
    for i, private_key in enumerate(private_keys, 1):
        print(f"\n{'='*60}")
        print(f"🔍 Обрабатываем кошелек {i}/{len(private_keys)}")
        print(f"{'='*60}")
        try:
            check_and_process_wallet(w3, private_key)
        except Exception as e:
            print(f"❌ Ошибка обработки кошелька: {e}")
        
        if i < len(private_keys):
            random_delay(DELAY_BETWEEN_WALLETS)
    
    colored_print(f"\n{'='*60}", Colors.CYAN)
    colored_print("🎉 Обработка всех кошельков завершена!", Colors.GREEN + Colors.BOLD)
    colored_print("💰 Проверьте ваши кошельки на предмет выведенных средств", Colors.PURPLE)
    colored_print("🔗 Все транзакции доступны по ссылкам выше", Colors.CYAN)

if __name__ == "__main__":
    main()
