import os
import openai
import datetime
from dotenv import load_dotenv, find_dotenv


class OpenAIClient:
    """A class to handle OpenAI API interactions with automatic model selection based on date."""

    def __init__(self, api_key=None):
        """
        Initialize the OpenAI client.

        Args:
            api_key (str, optional): OpenAI API key. If not provided, will load from .env file.
        """
        # Load environment variables
        load_dotenv(find_dotenv())

        # Set API key
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "OpenAI API key is required. Set OPENAI_API_KEY environment variable or pass api_key parameter."
            )

        # Initialize OpenAI client
        self.client = openai.OpenAI(api_key=self.api_key)

        # Set model based on current date
        self._set_model()

    def _set_model(self):
        """Set the model based on the current date."""
        current_date = datetime.datetime.now().date()
        target_date = datetime.date(2024, 6, 12)

        if current_date > target_date:
            self.model = "gpt-3.5-turbo"
        else:
            self.model = "gpt-3.5-turbo-0301"

    def get_completion(self, prompt, model=None, temperature=1):
        """
        Get a completion from OpenAI API.

        Args:
            prompt (str): The prompt to send to the model
            model (str, optional): Model to use. If not provided, uses the default model.
            temperature (float): Controls randomness in the response (0-2)

        Returns:
            str: The model's response
        """
        messages = [{"role": "user", "content": prompt}]

        # Use provided model or default model
        model_to_use = model or self.model

        response = self.client.chat.completions.create(
            model=model_to_use,
            messages=messages,
            temperature=temperature
        )
        return response.choices[0].message.content

    def get_completion_with_system_message(
        self, system_message, user_message, model=None, temperature=1
    ):
        """
        Get a completion with a system message.

        Args:
            system_message (str): The system message to set context
            user_message (str): The user's message
            model (str, optional): Model to use. If not provided, uses the default model.
            temperature (float): Controls randomness in the response (0-2)

        Returns:
            str: The model's response
        """
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message},
        ]

        # Use provided model or default model
        model_to_use = model or self.model

        response = self.client.chat.completions.create(
            model=model_to_use,
            messages=messages,
            temperature=temperature,
        )
        return response.choices[0].message.content

    def get_current_model(self):
        """Get the current default model being used."""
        return self.model

    def update_model(self, new_model):
        """
        Update the default model.

        Args:
            new_model (str): The new model to use as default
        """
        self.model = new_model

    def reset_to_date_based_model(self):
        """Reset the model to the date-based selection."""
        self._set_model()


# Example usage and backward compatibility
def get_completion(prompt, model=None):
    """
    Backward compatibility function for the original get_completion.

    Args:
        prompt (str): The prompt to send to the model
        model (str, optional): Model to use

    Returns:
        str: The model's response
    """
    client = OpenAIClient()
    return client.get_completion(prompt, model=model)


if __name__ == "__main__":
    # Example usage
    client = OpenAIClient()

    # Test basic completion
    response = client.get_completion("What is 1+1?")
    print(f"Basic completion: {response}")

    # Test with system message
    response = client.get_completion_with_system_message(
        system_message="You are a helpful math tutor.", user_message="What is 2+2?"
    )
    print(f"System message completion: {response}")

    # Test backward compatibility
    response = get_completion("What is 3+3?")
    print(f"Backward compatibility: {response}")
