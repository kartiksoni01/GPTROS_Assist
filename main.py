import argparse
import roslibpy
import time
import speech_recognition as sr
from gtts import gTTS
import os

from ai_interface import AIInterface

def args_factory() -> argparse.Namespace:
    '''
    Declaring all the required and optional arguments.
    Get help by using 'python3 main.py -h'.
    '''
    parser = argparse.ArgumentParser()
    
    parser.add_argument('--key', type=str, required=True, help='OpenAI API key.')
    parser.add_argument('--model', type=str, default='gpt-3.5-turbo', help='OpenAI API model.')
    parser.add_argument('--host', type=str, default='localhost', help='ROS host.')
    parser.add_argument('--port', type=int, default='9090', help='ROS port.')
    
    args = parser.parse_args()
    return args

def listen_for_speech():
    r = sr.Recognizer()
    with sr.Microphone() as source:
        print("Listening for a command...")
        try:
            audio = r.listen(source, timeout=5)  # Record for a maximum of 5 seconds
        except sr.WaitTimeoutError:
            print("Listening timeout reached.")
            return None

    try:
        command = r.recognize_sphinx(audio)
        print("You said: " + command)
        return command
    except sr.UnknownValueError:
        print("Could not understand audio")
        return None

def speak(text):
    tts = gTTS(text)
    tts.save("response.mp3")
    os.system("mpg123 response.mp3")

def main() -> None:
    args = args_factory()
    
    publisher_topic = str(input('Topic for publishing messages (leave blank if not any) → '))
    service_topic = str(input('Topic for using services (leave blank if not any) → '))
    
    '''Setting up connection with the ROS server'''
    ros_client = roslibpy.Ros(host=args.host, port=args.port)
    ros_client.run()
    
    '''Creating an interface with ChatGPT'''
    openai_interface = AIInterface(key=args.key, model=args.model)
    
    while True:
        try:
            '''Getting all the required ROS2 interfaces using ChatGPT '''
            command = listen_for_speech()
            if command:
                print("Breaking down the goal and creating steps...")
                interfaces_list = openai_interface.get_interfaces(prompt=command)
                print("Done...\n")

                '''Iterating through the response by ChatGPT and taking required actions.'''
                for interface in interfaces_list:
                    interface_category = interface["category"]
                    interface_type = interface["type"]
                    interface_data = interface["data"]

                    if interface_category == "msg":
                        publisher = roslibpy.Topic(ros_client, publisher_topic, interface_type)
                        if ros_client.is_connected:
                            publisher.publish(roslibpy.Message(interface_data))
                    elif interface_category == "srv":
                        service = roslibpy.Service(ros_client, service_topic, interface_type)
                        request = roslibpy.ServiceRequest()
                        if ros_client.is_connected:
                            service.call(request=request)
                    else:
                        print("\nOops! We were facing some issues with this command. Try reframing.")
                        raise Exception
                    time.sleep(1)

                # Respond to the user with a spoken acknowledgment
                speak("Okay, doing the specified task.")
        except Exception:
            print("\nThank you for using ControllerGPT!\n")
            break

    ros_client.terminate()

if __name__ == '__main__':
    main()
