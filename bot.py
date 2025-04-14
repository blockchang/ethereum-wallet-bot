from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, CallbackContext
from web3 import Web3
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Your Alchemy API URL and Telegram API Key from .env
alchemy_url = f"https://eth-mainnet.alchemyapi.io/v2/{os.getenv('ALCHEMY_API_KEY')}"
telegram_api_key = os.getenv("TELEGRAM_API_KEY")

# Connect to the Ethereum network
w3 = Web3(Web3.HTTPProvider(alchemy_url))

# Function to resolve ENS name to Ethereum address
def resolve_ens(ens_name):
    try:
        address = w3.ens.address(ens_name)
        if address:
            return address
        else:
            return None
    except Exception as e:
        return str(e)

# Function to check if the Ethereum address is valid
def is_valid_eth_address(address: str):
    return address.startswith("0x") and len(address) == 42

# Function to handle /start command
async def start(update: Update, context: CallbackContext):
    await update.message.reply_text(
        "👋 Welcome! I'm your Ethereum helper bot.\n\n"
        "I can assist you with the following commands:\n"
        "💼 /portfolio - Check your Ethereum portfolio balance (Ethereum address or ENS name)\n"
        "🔑 /hash - Get details of a specific Ethereum transaction\n"
        "🆘 /help - Get help with using the bot\n\n"
        "Just send one of these commands, and I’ll guide you through the process!"
    )

# Function to handle /help command
async def help_command(update: Update, context: CallbackContext):
    await update.message.reply_text(
        "Here are the commands you can use:\n\n"
        "/portfolio - Check your Ethereum portfolio balance (Ethereum address or ENS name)\n"
        "/hash - Get details of a specific transaction (Provide the transaction hash)\n"
        "/help - Get help on using the bot\n\n"
        "To use the bot, simply type /portfolio, /hash, or send your Ethereum address or ENS name!"
    )

# Function to handle /portfolio command
async def portfolio(update: Update, context: CallbackContext):
    await update.message.reply_text("🔍 Please send your wallet address (Ethereum address or ENS name) to check your portfolio balance.")
    context.user_data['command'] = 'portfolio'  # Set state to listen for the address

# Function to handle /hash command (transaction hash)
async def transaction_hash(update: Update, context: CallbackContext):
    await update.message.reply_text("🔑 Please provide a valid Ethereum transaction hash. Example: /hash <transaction_hash>")
    context.user_data['command'] = 'hash'  # Set state to listen for the transaction hash

# Function to handle wallet address or transaction hash input
async def handle_wallet_or_hash(update: Update, context: CallbackContext):
    user_input = update.message.text.strip()

    if 'command' not in context.user_data:
        return  # No active command to handle

    command = context.user_data['command']

    try:
        if command == 'portfolio':
            await process_portfolio(update, user_input, context)
        elif command == 'hash':
            await process_transaction_hash(update, user_input, context)
    except Exception as e:
        await update.message.reply_text(f"❌ Oops! Something went wrong. Error: {str(e)}")

    # Reset the command state after processing
    del context.user_data['command']

# Function to process /portfolio
async def process_portfolio(update: Update, wallet_address: str, context: CallbackContext):
    await update.message.reply_text("🔄 Processing your portfolio... Please wait.")

    if '.eth' in wallet_address:
        # ENS name, resolve it
        ens_address = resolve_ens(wallet_address)
        if ens_address:
            portfolio = f"💰 ETH Balance: {w3.from_wei(w3.eth.get_balance(ens_address), 'ether')} ETH"
            await update.message.reply_text(f"Your portfolio:\n{portfolio}\nENS Verified: {ens_address}")
        else:
            await update.message.reply_text("⚠️ ENS name is not registered or invalid.")
    else:
        # Ethereum address - Simplified validation
        if is_valid_eth_address(wallet_address):
            portfolio = f"💰 ETH Balance: {w3.from_wei(w3.eth.get_balance(wallet_address), 'ether')} ETH"
            ens_address = resolve_ens(wallet_address)
            if ens_address:
                await update.message.reply_text(f"Your portfolio:\n{portfolio}\nENS Verified: {ens_address}")
            else:
                await update.message.reply_text(f"Your portfolio:\n{portfolio}\nENS Verification: Not Found")
        else:
            await update.message.reply_text("⚠️ Invalid Ethereum address. Please try again.")

    # Call the function to show inline buttons after displaying the portfolio
    await send_inline_buttons(update)

# Function to process /hash (transaction hash)
async def process_transaction_hash(update: Update, tx_hash: str, context: CallbackContext):
    await update.message.reply_text("🔄 Processing the transaction details... Please wait.")

    if not tx_hash.startswith('0x') or len(tx_hash) != 66:
        await update.message.reply_text("⚠️ Invalid transaction hash format. Please provide a valid Ethereum transaction hash starting with '0x'.")
        return

    try:
        tx_details = w3.eth.get_transaction(tx_hash)
        if tx_details:
            sender = tx_details['from']
            recipient = tx_details['to']
            amount = w3.from_wei(tx_details['value'], 'ether')
            block_number = tx_details.get('blockNumber', 'Pending')  # Default value if blockNumber is missing

            # Check if the transaction is pending (no block number yet)
            if block_number == 'Pending':
                await update.message.reply_text(f"⏳ Transaction is still pending.\nSender: {sender}\nRecipient: {recipient}\nAmount: {amount} ETH")
                return

            await update.message.reply_text(
                f"🔑 Transaction Details:\nSender: {sender}\nRecipient: {recipient}\nAmount: {amount} ETH\nBlock Number: {block_number}"
            )
        else:
            await update.message.reply_text("⚠️ Transaction not found. Please ensure the transaction hash is correct and the transaction is confirmed.")
    except Exception as e:
        await update.message.reply_text(f"⚠️ Error: {str(e)}")

    # Call the function to show inline buttons after showing the transaction details
    await send_inline_buttons(update)

# Add inline buttons after processing a command
async def send_inline_buttons(update: Update):
    keyboard = [
        [InlineKeyboardButton("🔄 Check Another Portfolio", callback_data='/portfolio')],
        [InlineKeyboardButton("🔑 Check Another Transaction", callback_data='/hash')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Would you like to check another portfolio or transaction?", reply_markup=reply_markup)

# Handle inline button callback queries
async def button_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()  # Acknowledge the button press
    
    # Trigger the appropriate command based on the button clicked
    if query.data == '/portfolio':
        await query.edit_message_text("Please send your wallet address (Ethereum address or ENS name).")
        context.user_data['command'] = 'portfolio'
    
    elif query.data == '/hash':
        await query.edit_message_text("Please provide a valid transaction hash. Example: /hash <transaction_hash>")
        context.user_data['command'] = 'hash'

# Main function to set up the bot
def main():
    application = Application.builder().token(telegram_api_key).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("portfolio", portfolio))
    application.add_handler(CommandHandler("hash", transaction_hash))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_wallet_or_hash))

    # Add handler for inline button callback
    application.add_handler(CallbackQueryHandler(button_callback))  # Use CallbackQueryHandler for inline buttons

    # Start the bot
    application.run_polling()

if __name__ == '__main__':
    main()
