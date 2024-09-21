import sys
import math
from tabulate import tabulate
import mnemonic
from hashlib import sha256

# Define ANSI escape codes for console output
CLEAR_LINE = "\033[K"
MOVE_CURSOR_UP = "\033[F"

def get_user_dice_roll(roll_count, total_bits_needed, bits_generated):
    while True:
        progress = (bits_generated / total_bits_needed) * 100 if total_bits_needed else 0
        # Create a simple text-based progress bar
        bar_length = 20
        filled_length = int(bar_length * progress / 100)
        bar = '█' * filled_length + '-' * (bar_length - filled_length)
        sys.stdout.write(f"\rProgress: [{bar}] {progress:.2f}%")
        sys.stdout.flush()
        
        roll_input = input(f"\nEnter roll {roll_count} (1-6, 'q' to quit): ").strip().lower()
        if roll_input == 'q':
            sys.exit("Exiting due to user request.")
        try:
            roll = int(roll_input)
            if 1 <= roll <= 6:
                sys.stdout.write("\r" + CLEAR_LINE + "\r")
                return roll
            else:
                print("Error: The number must be between 1 and 6.")
        except ValueError:
            print("Invalid input. Please enter a number or 'q' to quit.")


def get_user_entropy_choice():
    # This function allows the user to choose how many words they want in their mnemonic
    while True:
        choice_input = input(
            "Choose mnemonic length:\n1. 12 words\n2. 15 words\n3. 18 words\n4. 21 words\n5. 24 words\nEnter choice (1-5, 'q' to quit): ").strip().lower()
        if choice_input == 'q':
            sys.exit("Exiting due to user request.")
        try:
            choice = int(choice_input)
            if 1 <= choice <= 5:
                return [128, 160, 192, 224, 256][choice - 1]
            else:
                print("Please enter a number between 1 and 5.")
        except ValueError:
            print("Invalid input. Please enter a number or 'q' to quit.")


def generate_even_distribution_entropy(entropy_bits_needed):
    # Validate entropy choice
    if entropy_bits_needed not in [128, 160, 192, 224, 256]:
        raise ValueError("Invalid entropy length chosen.")

    # Calculate total bits including checksum
    bytes_needed = entropy_bits_needed // 8
    checksum_bits_needed = bytes_needed * 8 // 32
    total_bits_needed = bytes_needed * 8 + checksum_bits_needed

    dice_rolls = []
    entropy_bits = ''
    bits_generated = 0

    rolls_needed = math.ceil(total_bits_needed / math.log2(6))
    roll_pairs_needed = math.ceil(rolls_needed / 2)

    for roll_pair_count in range(1, roll_pairs_needed + 1):
        if bits_generated < total_bits_needed:
            roll1 = get_user_dice_roll(roll_pair_count * 2 - 1, total_bits_needed, bits_generated)
            roll2 = get_user_dice_roll(roll_pair_count * 2, total_bits_needed, bits_generated)
            dice_rolls.append((roll1, roll2))

            # Combine two dice rolls into a single number for entropy
            combined = (roll1 - 1) * 6 + (roll2 - 1)
            bit_string = format(combined, '05b') # Convert to 5-bit representation

            # Take only as many bits as needed to not exceed total_bits_needed
            bits_to_take = min(len(bit_string), total_bits_needed - bits_generated)
            entropy_bits += bit_string[:bits_to_take]
            bits_generated += bits_to_take

            # Debug print to show progress in entropy generation
            print(f"Debug: Current entropy length: {len(entropy_bits)} bits")

    # Ensure entropy_bits aligns with byte boundaries
    while len(entropy_bits) % 8 != 0:
        entropy_bits = entropy_bits[:-1]
    
    entropy_bytes = bytes(int(entropy_bits[i:i + 8], 2) for i in range(0, len(entropy_bits), 8))

    # Calculate checksum
    hash = sha256(entropy_bytes).digest()
    hash_bits = ''.join(format(byte, '08b') for byte in hash)
    checksum = hash_bits[:checksum_bits_needed]
    print(f"Debug: Checksum length: {len(checksum)} bits")

    full_entropy = entropy_bits + checksum
    
    # Ensure full_entropy is byte-aligned before conversion
    while len(full_entropy) % 8 != 0:
        full_entropy = full_entropy[:-1]

    print(f"Debug: Full entropy length before byte conversion: {len(full_entropy)} bits")

    entropy_bytes_with_checksum = bytes(int(full_entropy[i:i + 8], 2) for i in range(0, len(full_entropy), 8))

    # Ensure correct entropy length
    if len(entropy_bytes_with_checksum) not in [16, 20, 24, 28, 32]:
        target_length = min([16, 20, 24, 28, 32], key=lambda x: (abs(x - len(entropy_bytes_with_checksum)), x))
        if len(entropy_bytes_with_checksum) > target_length:
            entropy_bytes_with_checksum = entropy_bytes_with_checksum[:target_length]
        else:
            entropy_bytes_with_checksum += b'\x00' * (target_length - len(entropy_bytes_with_checksum))

    print(f"Debug: Final entropy bytes length: {len(entropy_bytes_with_checksum)} bytes")

    return entropy_bytes_with_checksum, dice_rolls, bits_generated


def generate_bip39_phrase(entropy_bytes):
    # Convert entropy bytes into a mnemonic phrase using the BIP39 standard
    mnemo = mnemonic.Mnemonic("english")
    mnemonic_words = mnemo.to_mnemonic(entropy_bytes)
    return mnemonic_words.split(), mnemonic_words


# Main execution block
if __name__ == "__main__":
    try:
        entropy_bits_needed = get_user_entropy_choice()
        entropy_bytes_with_checksum, dice_rolls, bits_generated = generate_even_distribution_entropy(
            entropy_bits_needed)
        print("\nDice rolling completed.")
        mnemonic_words, mnemonic_full = generate_bip39_phrase(entropy_bytes_with_checksum)
        print("All words of the mnemonic have been selected.")
        headers = ["Generated Mnemonic", "Entropy (Dice Rolls)"]
        table_data = [[" ".join(mnemonic_words), str(dice_rolls)]]
        print(tabulate(table_data, headers=headers, tablefmt="grid"))
    except Exception as e:
        print(f"\nAn error occurred: {e}")
    finally:
        input("Press Enter to exit...")
