import front_end as fe

def main():
    fe.front_end()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nProgram interrupted by user. Exiting...")
    except BaseException as e:
        print(f"\nAn unexpected error occurred: {e}")