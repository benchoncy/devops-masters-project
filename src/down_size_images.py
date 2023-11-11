from src.pipelines.utils import S3ImageLoader, s3
import io


def main():
    loader = S3ImageLoader(
        bucket_name="bstuart-masters-project-dataset",
        key_prefix="images/objects-in-the-lab/images/",
    )
    for key, image in loader:
        # Downsize image
        image.thumbnail((256, 256))
        filename = key.split("/")[-1]
        # Save image
        with io.BytesIO() as output:
            image.save(output, format="JPEG")
            image = output.getvalue()
        s3.put_object(
            Bucket="bstuart-masters-project-dataset",
            Key="images/objects-in-the-lab/images_small/" + filename,
            Body=image,
        )


if __name__ == "__main__":
    main()
