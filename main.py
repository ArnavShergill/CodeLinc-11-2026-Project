import AI_interact
import back_end
import front_end

def main():
    pass

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nProgram interrupted by user. Exiting...")
    except BaseException as e:
        print(f"\nAn unexpected error occurred: {e}")