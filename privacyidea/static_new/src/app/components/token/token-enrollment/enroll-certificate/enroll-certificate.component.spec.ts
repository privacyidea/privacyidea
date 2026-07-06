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

import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { signal } from "@angular/core";
import { TokenEnrollmentData } from "@app/mappers/token-api-payload/_token-api-payload.mapper";
import { CaConnectors } from "@services/ca-connector/ca-connector.service";
import { PiResponse } from "@app/app.component";
import { MockHttpResourceRef, MockPiResponse } from "@testing/mock-services/mock-utils";
import { EnrollCertificateComponent } from "./enroll-certificate.component";
import { TokenService } from "@services/token/token.service";
import { MockTokenService, MockSystemService } from "@testing/mock-services";
import { SystemService } from "@services/system/system.service";

type CaConnectorResourceValue = PiResponse<CaConnectors> | undefined;

describe("EnrollCertComponent", () => {
  let component: EnrollCertificateComponent;
  let fixture: ComponentFixture<EnrollCertificateComponent>;
  let systemServiceMock: MockSystemService;

  const basicOptions: TokenEnrollmentData = { type: "certificate" };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EnrollCertificateComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: TokenService, useClass: MockTokenService },
        { provide: SystemService, useClass: MockSystemService }
      ]
    }).compileComponents();

    systemServiceMock = TestBed.inject(SystemService) as unknown as MockSystemService;
    systemServiceMock.caConnectorResource = new MockHttpResourceRef<CaConnectorResourceValue>(undefined);
    fixture = TestBed.createComponent(EnrollCertificateComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  describe("ngOnInit with enrollmentData input", () => {
    it("should set initial values from enrollmentData", () => {
      fixture.componentRef.setInput("enrollmentData", {
        type: "certificate",
        caConnector: "connector-123",
        certTemplate: "template-abc"
      });
      component.ngOnInit();
      expect(component.caConnector()).toBe("connector-123");
      expect(component.certTemplate()).toBe("template-abc");
    });

    it("should ignore values from enrollmentData if they are undefined", () => {
      fixture.componentRef.setInput("enrollmentData", {
        type: "certificate",
        caConnector: undefined,
        certTemplate: undefined
      });
      component.ngOnInit();
      expect(component.caConnector()).toBe("");
      expect(component.certTemplate()).toBe("");
    });
  });

  describe("caConnectorOptions computed", () => {
    it("should return empty array when caConnectorResource has no value", () => {
      expect(component.caConnectorOptions()).toEqual([]);
    });

    it("should map connectorname from the resource value", () => {
      (systemServiceMock.caConnectorResource as MockHttpResourceRef<CaConnectorResourceValue>).set(
        MockPiResponse.fromValue([
          { connectorname: "conn-1" },
          { connectorname: "conn-2" }
        ] as unknown as CaConnectors)
      );
      const opts = component.caConnectorOptions();
      expect(opts).toEqual(["conn-1", "conn-2"]);
    });
  });

  describe("certTemplateOptions linkedSignal", () => {
    it("should return empty list when no caConnector is selected", () => {
      systemServiceMock.caConnectors = signal<CaConnectors>([]);
      expect(component.certTemplateOptions()).toEqual([]);
    });

    it("should expose templates keys of the selected connector", () => {
      systemServiceMock.caConnectors = signal<CaConnectors>([
        { connectorname: "conn-1", type: "local", data: {}, templates: { t1: {}, t2: {} } },
        { connectorname: "conn-2", type: "local", data: {}, templates: { t3: {} } }
      ]);
      component.caConnector.set("conn-1");
      expect(component.certTemplateOptions().sort()).toEqual(["t1", "t2"]);
    });
  });

  describe("buildEnrollmentArgs", () => {
    it("should return null and mark pem touched when uploadRequest selected but pem is empty", () => {
      component.intention.set("uploadRequest");
      component.pem.set("");
      const result = component.buildEnrollmentArgs(basicOptions);
      expect(result).toBeNull();
      expect(component.pemForm().touched()).toBe(true);
    });

    it("should return null and mark caConnectorTouched when generate but caConnector empty", () => {
      component.intention.set("generate");
      component.caConnector.set("");
      const result = component.buildEnrollmentArgs(basicOptions);
      expect(result).toBeNull();
      expect(component.caConnectorTouched()).toBe(true);
    });

    it("should return null and mark certTemplateTouched when generate but certTemplate empty", () => {
      component.intention.set("generate");
      component.caConnector.set("conn-1");
      component.certTemplate.set("");
      const result = component.buildEnrollmentArgs(basicOptions);
      expect(result).toBeNull();
      expect(component.certTemplateTouched()).toBe(true);
    });

    it("should return enrollment data without pem when intention is generate", () => {
      component.intention.set("generate");
      component.caConnector.set("conn-1");
      component.certTemplate.set("t1");
      const result = component.buildEnrollmentArgs(basicOptions);
      expect(result).not.toBeNull();
      expect(result!.data.caConnector).toBe("conn-1");
      expect(result!.data.certTemplate).toBe("t1");
      expect(result!.data.pem).toBeUndefined();
    });

    it("should include pem when intention is uploadCert", () => {
      component.intention.set("uploadCert");
      component.pem.set("-----BEGIN CERTIFICATE-----");
      const result = component.buildEnrollmentArgs(basicOptions);
      expect(result).not.toBeNull();
      expect(result!.data.pem).toBe("-----BEGIN CERTIFICATE-----");
    });
  });

  describe("clearTemplateSelection", () => {
    it("should reset certTemplate to empty string", () => {
      component.certTemplate.set("t1");
      component.clearTemplateSelection();
      expect(component.certTemplate()).toBe("");
    });
  });
});
