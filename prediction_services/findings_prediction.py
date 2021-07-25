import sys
import pika
import main_operations
from params_reader import get_param

# this dictionary contains mapping for workers and their respective functions
# please make sure to change this dictionary in case of changing functions' names
input_to_function = {"import": "import_and_train",
                     "export": "show_and_export",
                     "storage": "create_directory"}


def publish(ch, method, props, result):
    ch.basic_publish(exchange='',
                     routing_key=props.reply_to,
                     properties=pika.BasicProperties(
                         correlation_id=props.correlation_id),
                     body=str(result))
    ch.basic_ack(delivery_tag=method.delivery_tag)


def import_and_train(ch, method, props, body):
    print("Received", body.decode("utf-8"))
    shape_folder = body.decode("utf-8")
    try:
        main_operations.extract_data(shape_folder)
        main_operations.generate_models(shape_folder)
        result = "Success," + shape_folder
    except Exception as e:
        result = e
        main_operations.remove_subdirectory(get_param("main_directory") + shape_folder)

    # print(result)
    publish(ch, method, props, result)


def show_and_export(ch, method, props, body):
    print("Received", body.decode("utf-8"))
    data = body.decode("utf-8").split(",")
    if data[0] == get_param("get_species_keyword"):
        result = main_operations.get_species(data[1])
    else:
        try:
            shape_folder, species, color, result_folder = data[0], data[1].split(";"), get_param("map_colors")[data[2]], data[3]
            destination = main_operations.generate_predictions(shape_folder, species, color, result_folder)
            result = "Success," + str(destination)
        except Exception as e:
            result = e
            main_operations.remove_subdirectory(get_param("result_directory") + shape_folder)
    # print(result)
    publish(ch, method, props, str(result))


def create_directory(ch, method, props, body):
    print("Received", body.decode("utf-8"))
    data = body.decode("utf-8")
    if data == "import":
        result = main_operations.create_subdirectory(get_param("main_directory"))
        if get_param("rabbit_host") != "localhost":
            result = result + "," + get_param("upload_URL")
    elif data == "export":
        result = main_operations.create_subdirectory(get_param("result_directory"))
        if get_param("rabbit_host") != "localhost":
            result = result + "," + get_param("download_URL")
    else:
        result = ""
    # print(result)
    publish(ch, method, props, result)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Not enough arguments, proper execution: python rabbit_ml_test <worker_type>")
    elif len(sys.argv) > 2:
        print("Too many arguments, proper execution: python rabbit_ml_test <worker_type>")
    else:
        worker_type = sys.argv[1]
        if worker_type not in input_to_function.keys():
            print("Worker type does not exist")
        else:
            # all logic behind defining RabbitMQ, using an exchange and multiple anonymous channels
            connection = pika.BlockingConnection(pika.ConnectionParameters(host=get_param("rabbit_host"), heartbeat=0))
            channel = connection.channel()
            channel.exchange_declare(exchange=get_param("rabbit_exchange"), exchange_type='direct')  # consider 'topic'
            queue_result = channel.queue_declare(queue='', exclusive=True)
            queue_name = queue_result.method.queue
            channel.basic_qos(prefetch_count=1)
            channel.queue_bind(exchange=get_param("rabbit_exchange"), queue=queue_name, routing_key=worker_type)

            try:
                channel.basic_consume(queue=queue_name, on_message_callback=eval(input_to_function[worker_type]))
                print("RPC Server is ready for use")
                channel.start_consuming()
            except KeyboardInterrupt:
                print("Program is ending")
                channel.close()
                connection.close()
                sys.exit(0)
