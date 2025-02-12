from .note import UnresolvedReference, ExternalReference

class AttachmentMixin:
    def persist_attachments(self, location):
        updated_attachments = []
        for attachment in self.attachments:
            if isinstance(attachment, UnresolvedReference):
                print(f"I'm totes saving {attachment} to s3 instead of  {location}")
                url = "https://example.com/test.png"
                updated_attachments.append(ExternalReference(url=url))
            else:
                updated_attachments.append(attachment)
        self.attachments = updated_attachments
