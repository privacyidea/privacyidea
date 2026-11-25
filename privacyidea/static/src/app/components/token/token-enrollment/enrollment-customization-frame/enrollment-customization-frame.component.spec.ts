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

import { provideHttpClient } from "@angular/common/http";
import { HttpTestingController, provideHttpClientTesting } from "@angular/common/http/testing";
import { Component, signal } from "@angular/core";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { EnrollmentResponseDetail } from "@app/mappers/token-api-payload/_token-api-payload.mapper";
import { environment } from "@env/environment";
import { EnrollmentCustomizationFrameComponent } from "./enrollment-customization-frame.component";

@Component({
  imports: [EnrollmentCustomizationFrameComponent],
  template: `<app-enrollment-customization-frame
    [enabled]="enabled()"
    [enrollmentDetail]="detail"
    ><p class="step-content">Step</p></app-enrollment-customization-frame
  >`
})
class HostComponent {
  enabled = signal(true);
  detail: EnrollmentResponseDetail | undefined = {
    serial: "OATH0001",
    googleurl: { description: "", img: "data:image/png;base64,QR", value: "otpauth://hotp/OATH0001" }
  } as unknown as EnrollmentResponseDetail;
}

describe("EnrollmentCustomizationFrameComponent", () => {
  let fixture: ComponentFixture<HostComponent>;
  let httpMock: HttpTestingController;
  const customizationUrl = (position: string) =>
    environment.proxyUrl + `/static/public/customize/token-enrollment.wizard.post.${position}.html`;

  const setup = async (enabled: boolean, detail?: EnrollmentResponseDetail | null) => {
    await TestBed.configureTestingModule({
      imports: [HostComponent],
      providers: [provideHttpClient(), provideHttpClientTesting()]
    }).compileComponents();
    fixture = TestBed.createComponent(HostComponent);
    fixture.componentInstance.enabled.set(enabled);
    if (detail !== undefined) {
      fixture.componentInstance.detail = detail ?? undefined;
    }
    httpMock = TestBed.inject(HttpTestingController);
    fixture.detectChanges();
  };

  const settle = async () => {
    await fixture.whenStable();
    fixture.detectChanges();
  };

  afterEach(() => httpMock.verify());

  it("puts the post customization around the step and fills in its tags", async () => {
    await setup(true);
    httpMock.expectOne(customizationUrl("top")).flush("<p class='top'>{{ serial }} {{url}}</p>");
    httpMock.expectOne(customizationUrl("bottom")).flush("<p class='bottom'>Bottom</p>");
    await settle();

    const element: HTMLElement = fixture.nativeElement;
    const paragraphs = Array.from(element.querySelectorAll("p")).map((p) => p.className);
    expect(paragraphs).toEqual(["top", "step-content", "bottom"]);
    expect(element.querySelector(".top")?.textContent).toBe("OATH0001 otpauth://hotp/OATH0001");
  });

  it("takes the QR code and URL from whichever enrollment URL the token type returns", async () => {
    await setup(true, {
      serial: "TIQR0001",
      tiqrenroll: { description: "", img: "data:image/png;base64,TIQR", value: "tiqrenroll://TIQR0001" }
    } as unknown as EnrollmentResponseDetail);
    httpMock.expectOne(customizationUrl("top")).flush("<p class='top'>{{ url }}</p><img src='{{ qrCode }}'>");
    httpMock.expectOne(customizationUrl("bottom")).flush("");
    await settle();

    const element: HTMLElement = fixture.nativeElement;
    expect(element.querySelector(".top")?.textContent).toBe("tiqrenroll://TIQR0001");
    expect(element.querySelector("img")?.getAttribute("src")).toBe("data:image/png;base64,TIQR");
  });

  it("fills in empty tags without enrollment details", async () => {
    await setup(true, null);
    httpMock.expectOne(customizationUrl("top")).flush("<p class='top'>[{{ serial }}|{{ url }}|{{ qrCode }}]</p>");
    httpMock.expectOne(customizationUrl("bottom")).flush("");
    await settle();

    expect(fixture.nativeElement.querySelector(".top")?.textContent).toBe("[||]");
  });

  it("leaves out an empty customization", async () => {
    await setup(true);
    httpMock.expectOne(customizationUrl("top")).flush("  \n");
    httpMock.expectOne(customizationUrl("bottom")).flush("");
    await settle();

    expect(fixture.nativeElement.querySelectorAll("div").length).toBe(0);
    expect(fixture.nativeElement.querySelector(".step-content")).not.toBeNull();
  });

  it("leaves out a customization that cannot be loaded", async () => {
    await setup(true);
    httpMock.expectOne(customizationUrl("top")).flush("", { status: 404, statusText: "Not Found" });
    httpMock.expectOne(customizationUrl("bottom")).flush("", { status: 404, statusText: "Not Found" });
    await settle();

    expect(fixture.nativeElement.querySelectorAll("div").length).toBe(0);
    expect(fixture.nativeElement.querySelector(".step-content")).not.toBeNull();
  });

  it("removes scripts from the customization", async () => {
    await setup(true);
    httpMock.expectOne(customizationUrl("top")).flush("<p class='top'>Top</p><script>alert(1)</script>");
    httpMock.expectOne(customizationUrl("bottom")).flush("");
    await settle();

    expect(fixture.nativeElement.querySelector("script")).toBeNull();
    expect(fixture.nativeElement.querySelector(".top")).not.toBeNull();
  });

  it("only shows the step outside the wizard", async () => {
    await setup(false);
    await settle();

    expect(fixture.nativeElement.querySelector(".step-content")).not.toBeNull();
    expect(fixture.nativeElement.querySelectorAll("div").length).toBe(0);
  });
});
