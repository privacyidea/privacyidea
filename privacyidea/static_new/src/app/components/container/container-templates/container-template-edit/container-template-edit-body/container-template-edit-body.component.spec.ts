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
import { ContainerTemplate } from "../../../../../services/container/container.service";
import { ContainerTemplateEditBodyComponent } from "./container-template-edit-body.component";
import { TokenService, TokenTypeKey } from "@services/token/token.service";
import { MockSystemService, MockTokenService } from "@testing/mock-services";
import { SystemService } from "@services/system/system.service";
import { TokenEnrollmentPayload } from "@app/mappers/token-api-payload/_token-api-payload.mapper";

const baseTemplate: ContainerTemplate = {
  name: "Test",
  container_type: "generic",
  default: false,
  template_options: {
    tokens: [
      { type: "hotp" } as unknown as TokenEnrollmentPayload,
      { type: "totp" } as unknown as TokenEnrollmentPayload
    ]
  }
};

type TestableBody = ContainerTemplateEditBodyComponent & {
  tokens: () => TokenEnrollmentPayload[];
  onAddToken: (type: TokenTypeKey | string) => void;
  onDeleteToken: (index: number) => void;
  onEditToken: (patch: Partial<TokenEnrollmentPayload>, index: number) => void;
};

describe("ContainerTemplateEditBodyComponent", () => {
  let component: ContainerTemplateEditBodyComponent;
  let fixture: ComponentFixture<ContainerTemplateEditBodyComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ContainerTemplateEditBodyComponent],
      providers: [
        { provide: TokenService, useClass: MockTokenService },
        { provide: SystemService, useClass: MockSystemService }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(ContainerTemplateEditBodyComponent);
    component = fixture.componentInstance;

    fixture.componentRef.setInput("template", {
      ...baseTemplate,
      template_options: { tokens: [...baseTemplate.template_options.tokens] }
    });
    fixture.componentRef.setInput("availableTokenTypes", ["hotp", "totp"]);
    fixture.detectChanges();
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("onAddToken appends a new token with the given type", () => {
    const testable = component as TestableBody;
    const before = testable.tokens().length;
    testable.onAddToken("hotp");
    expect(testable.tokens().length).toBe(before + 1);
    expect(testable.tokens()[before].type).toBe("hotp");
    expect(component.template().template_options.tokens.length).toBe(before + 1);
    expect(component.template().template_options.tokens[before].type).toBe("hotp");
  });

  it("onDeleteToken removes the token at the given index", () => {
    const testable = component as TestableBody;
    const before = testable.tokens().length;
    testable.onDeleteToken(0);
    expect(testable.tokens().length).toBe(before - 1);
    expect(testable.tokens()[0].type).toBe("totp");
    expect(component.template().template_options.tokens.length).toBe(before - 1);
    expect(component.template().template_options.tokens[0].type).toBe("totp");
  });

  it("onEditToken merges a patch into the token at the given index", () => {
    const testable = component as TestableBody;
    testable.onEditToken({ description: "Edited" }, 0);
    expect(testable.tokens()[0].description).toBe("Edited");
    expect(testable.tokens()[0].type).toBe("hotp");
    expect(component.template().template_options.tokens[0].description).toBe("Edited");
    expect(component.template().template_options.tokens[0].type).toBe("hotp");
  });

  it("onEditToken removes undefined keys from the patched token", () => {
    const testable = component as TestableBody;
    testable.onEditToken({ type: undefined }, 0);
    expect("type" in testable.tokens()[0]).toBe(false);
    expect("type" in component.template().template_options.tokens[0]).toBe(false);
  });
});
