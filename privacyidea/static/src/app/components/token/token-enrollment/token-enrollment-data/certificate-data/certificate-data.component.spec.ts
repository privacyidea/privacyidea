/**
 * (c) NetKnights GmbH 2026,  https://netknights.it
 *
 * This code is free software; you can redistribute it and/or
 * modify it under the terms of the GNU AFFERO GENERAL PUBLIC LICENSE
 * as published by the Free Software Foundation; either
 * version 3 of the License, or any later version.
 *
 * This code is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 * GNU AFFERO GENERAL PUBLIC LICENSE for more details.
 *
 * You should have received a copy of the GNU Affero General Public
 * License along with this program.  If not, see <http://www.gnu.org/licenses/>.
 *
 * SPDX-License-Identifier: AGPL-3.0-or-later
 **/
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { By } from "@angular/platform-browser";
import { CopyButtonComponent } from "@components/shared/copy-button/copy-button.component";
import { NotificationService } from "@services/notification/notification.service";
import { MockNotificationService } from "@testing/mock-services";
import { OBJECT_URL_LIFETIME_MS } from "@utils/download.utils";
import { CertificateDataComponent } from "./certificate-data.component";
import { axe } from "@testing/axe";

const CERTIFICATE = "-----BEGIN CERTIFICATE-----\nMIIBdummy\n-----END CERTIFICATE-----";
const PKCS12 = "AAECAw==";
const PKCS12_BYTES = [0, 1, 2, 3];
const PASSPHRASE = "s3cret-passphrase";

describe("CertificateDataComponent", () => {
  let component: CertificateDataComponent;
  let fixture: ComponentFixture<CertificateDataComponent>;
  let notificationService: MockNotificationService;

  let unsavedData: string[];
  let closeConfirmations: string[];
  let downloads: { fileName: string; blob: Blob }[];
  let revokedUrls: string[];

  const lastUnsaved = () => unsavedData.at(-1);

  const setInputs = (inputs: Record<string, string | boolean>) => {
    Object.entries(inputs).forEach(([name, value]) => fixture.componentRef.setInput(name, value));
    fixture.detectChanges();
  };

  // The Blob of this jsdom build offers neither text() nor arrayBuffer(), so downloads are
  // read back through FileReader.
  const readBlob = <T>(blob: Blob, read: (reader: FileReader) => void) =>
    new Promise<T>((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result as T);
      reader.onerror = () => reject(reader.error);
      read(reader);
    });

  const readBlobText = (blob: Blob) => readBlob<string>(blob, (reader) => reader.readAsText(blob));

  const readBlobBytes = async (blob: Blob) =>
    Array.from(new Uint8Array(await readBlob<ArrayBuffer>(blob, (reader) => reader.readAsArrayBuffer(blob))));

  const passwordCopyButton = () =>
    fixture.debugElement
      .queryAll(By.directive(CopyButtonComponent))
      .map((element) => element.componentInstance as CopyButtonComponent)
      .find((copyButton) => copyButton.copyText() === PASSPHRASE)!;

  beforeEach(async () => {
    unsavedData = [];
    closeConfirmations = [];
    downloads = [];
    revokedUrls = [];

    const blobsByUrl = new Map<string, Blob>();
    let urlCount = 0;
    Object.defineProperty(window.URL, "createObjectURL", {
      configurable: true,
      writable: true,
      value: jest.fn((blob: Blob) => {
        const url = `blob:certificate-data/${++urlCount}`;
        blobsByUrl.set(url, blob);
        return url;
      })
    });
    Object.defineProperty(window.URL, "revokeObjectURL", {
      configurable: true,
      writable: true,
      value: jest.fn((url: string) => revokedUrls.push(url))
    });
    jest.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(function (this: HTMLAnchorElement) {
      downloads.push({ fileName: this.download, blob: blobsByUrl.get(this.getAttribute("href") ?? "")! });
    });

    await TestBed.configureTestingModule({
      imports: [CertificateDataComponent],
      providers: [{ provide: NotificationService, useClass: MockNotificationService }]
    }).compileComponents();

    notificationService = TestBed.inject(NotificationService) as unknown as MockNotificationService;

    fixture = TestBed.createComponent(CertificateDataComponent);
    component = fixture.componentInstance;
    component.unsavedDataChange.subscribe((unsaved) => unsavedData.push(unsaved));
    component.closeConfirmationChange.subscribe((message) => closeConfirmations.push(message));
  });

  afterEach(() => {
    jest.useRealTimers();
    jest.restoreAllMocks();
  });

  it("should create", () => {
    fixture.detectChanges();
    expect(component).toBeTruthy();
  });

  describe("unsaved data", () => {
    it("reports nothing when there is nothing to save", () => {
      setInputs({ serial: "CRT0001", rolloutState: "enrolled" });
      expect(lastUnsaved()).toBe("");
    });

    it("reports the certificate until it has been downloaded", () => {
      setInputs({ serial: "CRT0001", certificate: CERTIFICATE });
      expect(lastUnsaved()).toBe("Download the certificate.");

      component.downloadCertificate();
      fixture.detectChanges();
      expect(lastUnsaved()).toBe("");
    });

    it("accepts showing the certificate instead of downloading it", () => {
      setInputs({ serial: "CRT0001", certificate: CERTIFICATE });
      expect(lastUnsaved()).toBe("Download the certificate.");

      const header = fixture.debugElement.query(By.css(".certificate-expansion mat-expansion-panel-header"))
        .nativeElement as HTMLElement;
      header.click();
      header.click();
      fixture.detectChanges();
      expect(lastUnsaved()).toBe("");
      expect(downloads).toEqual([]);
    });

    it("reports the PKCS#12 container until it has been downloaded", () => {
      setInputs({ serial: "CRT0001", pkcs12: PKCS12 });
      expect(lastUnsaved()).toBe("Download the PKCS#12 file.");

      component.downloadPkcs12();
      fixture.detectChanges();
      expect(lastUnsaved()).toBe("");
    });

    it("reports the passphrase until it has been revealed", () => {
      setInputs({ serial: "CRT0001", pkcs12: PKCS12, pkcs12Password: PASSPHRASE });
      component.downloadPkcs12();
      fixture.detectChanges();
      expect(lastUnsaved()).toBe("Show or copy the passphrase.");

      fixture.debugElement.query(By.css(".enrollment-secret__toggle")).nativeElement.click();
      fixture.detectChanges();
      expect(lastUnsaved()).toBe("");
    });

    it("accepts copying the passphrase instead of revealing it", () => {
      setInputs({ serial: "CRT0001", pkcs12: PKCS12, pkcs12Password: PASSPHRASE });
      component.downloadPkcs12();
      fixture.detectChanges();

      passwordCopyButton().onCopy();
      fixture.detectChanges();
      expect(lastUnsaved()).toBe("");
    });

    it("keeps the passphrase acknowledged after hiding it again", () => {
      setInputs({ serial: "CRT0001", pkcs12: PKCS12, pkcs12Password: PASSPHRASE });
      component.downloadPkcs12();
      fixture.detectChanges();
      const toggle = fixture.debugElement.query(By.css(".enrollment-secret__toggle"))
        .nativeElement as HTMLButtonElement;
      toggle.click();
      toggle.click();
      fixture.detectChanges();

      expect(toggle.getAttribute("aria-label")).toBe("Show Passphrase");
      expect(lastUnsaved()).toBe("");
    });

    it("lists every outstanding step and drops each one as it is done", () => {
      setInputs({
        serial: "CRT0001",
        certificate: CERTIFICATE,
        pkcs12: PKCS12,
        pkcs12Password: PASSPHRASE
      });
      expect(lastUnsaved()).toBe("Download the certificate. Download the PKCS#12 file. Show or copy the passphrase.");

      component.downloadCertificate();
      fixture.detectChanges();
      expect(lastUnsaved()).toBe("Download the PKCS#12 file. Show or copy the passphrase.");

      component.acknowledgePassword();
      fixture.detectChanges();
      expect(lastUnsaved()).toBe("Download the PKCS#12 file.");

      component.downloadPkcs12();
      fixture.detectChanges();
      expect(lastUnsaved()).toBe("");
    });

    it("stops reporting a PKCS#12 container that cannot be decoded", () => {
      setInputs({ serial: "CRT0001", pkcs12: "not base64!!" });
      expect(lastUnsaved()).toBe("Download the PKCS#12 file.");

      component.downloadPkcs12();
      fixture.detectChanges();

      expect(downloads).toHaveLength(0);
      expect(notificationService.error).toHaveBeenCalledWith(
        "The PKCS#12 container of this token is damaged and cannot be downloaded."
      );
      expect(lastUnsaved()).toBe("");
    });
  });

  describe("close confirmation", () => {
    it("asks before closing only while the passphrase has not been taken note of", () => {
      setInputs({ serial: "CRT0001", pkcs12: PKCS12, pkcs12Password: PASSPHRASE });
      expect(closeConfirmations.at(-1)).toContain("shown only once");

      passwordCopyButton().onCopy();
      fixture.detectChanges();
      expect(closeConfirmations.at(-1)).toBe("");
    });

    it("does not ask for files that stay available in the token details", () => {
      setInputs({ serial: "CRT0001", certificate: CERTIFICATE, pkcs12: PKCS12 });
      expect(lastUnsaved()).not.toBe("");
      expect(closeConfirmations.at(-1)).toBe("");
    });
  });

  describe("downloads", () => {
    it("writes the certificate as a PEM file named after the serial", async () => {
      setInputs({ serial: "CRT0001", certificate: CERTIFICATE });

      component.downloadCertificate();

      expect(downloads).toHaveLength(1);
      expect(downloads[0].fileName).toBe("CRT0001.pem");
      expect(downloads[0].blob.type).toBe("application/x-pem-file");
      await expect(readBlobText(downloads[0].blob)).resolves.toBe(CERTIFICATE);
    });

    it("writes the decoded container as a PKCS#12 file named after the serial", async () => {
      setInputs({ serial: "CRT0001", pkcs12: PKCS12 });

      component.downloadPkcs12();

      expect(downloads).toHaveLength(1);
      expect(downloads[0].fileName).toBe("CRT0001.p12");
      expect(downloads[0].blob.type).toBe("application/x-pkcs12");
      await expect(readBlobBytes(downloads[0].blob)).resolves.toEqual(PKCS12_BYTES);
    });

    it("falls back to a generic file name when the serial is unknown", () => {
      setInputs({ certificate: CERTIFICATE, pkcs12: PKCS12 });

      component.downloadCertificate();
      component.downloadPkcs12();

      expect(downloads.map((download) => download.fileName)).toEqual(["certificate.pem", "certificate.p12"]);
    });

    it("revokes the object URL of every download", () => {
      setInputs({ serial: "CRT0001", certificate: CERTIFICATE, pkcs12: PKCS12 });
      jest.useFakeTimers();

      component.downloadCertificate();
      component.downloadPkcs12();
      jest.advanceTimersByTime(OBJECT_URL_LIFETIME_MS);

      expect(revokedUrls).toEqual(["blob:certificate-data/1", "blob:certificate-data/2"]);
    });
  });

  describe("template", () => {
    it("explains a request that is still waiting for the certificate authority", () => {
      setInputs({ serial: "CRT0001", rolloutState: "pending" });

      expect(fixture.nativeElement.textContent).toContain("waiting for approval by the certificate authority");
      expect(fixture.debugElement.query(By.css(".certificate-actions"))).toBeNull();
    });

    it("reports a denied request", () => {
      setInputs({ serial: "CRT0001", rolloutState: "denied" });

      expect(fixture.nativeElement.textContent).toContain("denied this request");
    });

    it("reports a failed request", () => {
      setInputs({ serial: "CRT0001", rolloutState: "failed" });

      expect(fixture.nativeElement.textContent).toContain("request to the certificate authority failed");
    });

    it("shows the passphrase masked, with the hint to save it", () => {
      setInputs({ serial: "CRT0001", pkcs12: PKCS12, pkcs12Password: PASSPHRASE });

      expect(fixture.nativeElement.querySelector("app-enrollment-secret code").textContent).toBe(
        "•".repeat(PASSPHRASE.length)
      );
      expect(fixture.nativeElement.textContent).toContain("Save the passphrase of the PKCS#12 container now.");
    });

    it("leaves out the hint when asked to", () => {
      setInputs({ serial: "CRT0001", pkcs12: PKCS12, pkcs12Password: PASSPHRASE, saveHint: false });

      expect(fixture.nativeElement.querySelector("app-enrollment-secret")).toBeTruthy();
      expect(fixture.nativeElement.textContent).not.toContain("Save the passphrase");
    });

    it("points to the token PIN when the container has no separate passphrase", () => {
      setInputs({ serial: "CRT0001", pkcs12: PKCS12, fromEnrollment: true });

      expect(fixture.nativeElement.textContent).toContain("passphrase of the PKCS#12 container is the token PIN");
      expect(fixture.debugElement.query(By.css("app-enrollment-secret"))).toBeNull();
    });

    it("stays silent about the passphrase outside the enrollment response", () => {
      setInputs({ serial: "CRT0001", pkcs12: PKCS12 });

      expect(fixture.nativeElement.textContent).not.toContain("is the token PIN");
    });

    it("promises only the private key while the request is pending", () => {
      setInputs({ serial: "CRT0001", pkcs12: PKCS12, rolloutState: "pending" });

      expect(fixture.nativeElement.textContent).toContain("The PKCS#12 container holds the private key.");
      expect(fixture.nativeElement.textContent).not.toContain("private key and the certificate");
    });
  });

  it("passes the axe accessibility checks", async () => {
    fixture.detectChanges();

    expect(await axe(fixture.nativeElement)).toHaveNoViolations();
  });
});
