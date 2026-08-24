print("Welcome to Choose Your Own!")
name = input("What is your name? ")
print(f"Hello {name}!")
age = int(input("What is your age? "))

health = 10

is_older = age >= 18

if is_older:
    print("You are old enough to play!")

    wants_to_play = input("Do you want to play? ").lower()
    if(wants_to_play == "yes"):
        print("Lets play!")
        print("You start with", health, "health, good luck.")

        left_or_right = input("First choice... Left or Right(left/right)? ").lower()
        if left_or_right == "left":
            ans = input("Nice, you follow the path and reach a lake... Do you swim across or go around (across/around)? ").lower()

            if ans == "around":
                print("You went around and reached the other side of the lake")
            elif ans == "across":
                print("You managed to get across but were bit by something and lost 5 health")
                health -= 5
                print("You currently have", health, "health left")

            ans = input("You see a river and a house which do you go to (river/house)?" )
            if ans == "house":
                print("You go to the house and the owner strikes you for 5 health")
                health -= 5

                if health <= 0:
                    print("You have 0 health and lost the game...")
                else:
                    print("You survived and won the game!")
                    
            else:
                print("You fell in the river and lost...")
            
        else:
            print("You fell down and lost...")

    else:
        print("Ok that's fine. Bye")

else: 
    print("You are too young to play this game!")