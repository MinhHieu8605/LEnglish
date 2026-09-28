from email.message import EmailMessage
from email.utils import formataddr
import mimetypes
import os

import aiofiles
import aiosmtplib

from app.config.settings import SmtpEmailConfig
from app.utils.constants import FileMode

email_config = SmtpEmailConfig()


class EmailService(object):
    """Service class for sending emails using an email provider."""

    async def create_attachment(self, file_path: str) -> dict:
        """
        Create an email attachment.

        Args:
            file_path (str): The path to the file to be attached.

        Returns:
            dict: A dictionary representing the attachment.
        """
        if not os.path.isfile(file_path):
            raise FileNotFoundError(f"The file {file_path} does not exist.")

        async with aiofiles.open(file_path, FileMode.READ_BINARY) as file:
            content = await file.read()

        if not content:
            raise ValueError(f"The file {file_path} is empty.")

        content_type = (
            mimetypes.guess_type(file_path)[0] 
            or "application/octet-stream"
        )
        maintype, subtype = content_type.split("/", maxsplit=1)

        return {
            "content": content,
            "maintype": maintype,
            "subtype": subtype,
            "filename": os.path.basename(file_path),
        }


    async def send_email(self, payload: dict) -> None:
        """
        Send an email using the provided payload.

        Args:
            payload (dict): A dictionary containing email details such as
                            subject, body, recipients, and attachments.

        Raises:
            NotImplementedError: This method should be implemented by subclasses.
        """
        message = EmailMessage()

        message["From"] = formataddr(("Feedback feature", email_config.smtp_sender))
        message["To"] = payload["to"].replace(";", ",")
        message["Cc"] = payload.get("cc", "").replace(";", ",")
        message["Subject"] = payload["subject"]
        message.set_content(payload.get("body", ""), subtype="html")

        for attachment in payload.get("attachments", []):
            message.add_attachment(
                attachment["content"],
                maintype=attachment["maintype"],
                subtype=attachment["subtype"],
                filename=attachment["filename"],
            )

        use_tls = email_config.smtp_port == 465

        await aiosmtplib.send(
            message,
            hostname=email_config.smtp_host,
            port=email_config.smtp_port,
            username=email_config.smtp_user,
            password=email_config.smtp_password,
            use_tls=use_tls,
            start_tls=email_config.smtp_use_tls and not use_tls,
        )

email_service = EmailService()
