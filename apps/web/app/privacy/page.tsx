export default function PrivacyPage() {
  return (
    <main className="page legal-page">
      <p className="kicker">Hyderabad</p>
      <h1>Privacy & Terms</h1>
      <h2>Privacy</h2>
      <p>
        Photos you upload are stored so others in your 20 km circle can see the issue. We re-encode
        images and strip EXIF GPS so the file itself does not leak a precise camera location.
      </p>
      <p>
        The pin is the latitude and longitude you allow, or the point you drop inside that circle.
        We also store the nearest GHMC circle and ward name for that pin.
      </p>
      <h2>Terms</h2>
      <p>
        FixMyTown is a civic prototype for Hyderabad. It is not a GHMC website. There is no
        service-level agreement and no official relationship with GHMC.
      </p>
      <p>
        Reports have to sit inside Hyderabad and inside 20 km of your live location. Pins outside
        that circle are rejected. Do not upload images of people or plates if you can avoid it.
      </p>
    </main>
  );
}
