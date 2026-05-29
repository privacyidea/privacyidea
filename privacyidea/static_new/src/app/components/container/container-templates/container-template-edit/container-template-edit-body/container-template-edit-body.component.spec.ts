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
import { TokenEnrollmentPayload } from "@app/mappers/token-api-payload/_token-api-payload.mapper";
import { SystemService } from "@services/system/system.service";
import { TokenService } from "@services/token/token.service";
import { MockSystemService, MockTokenService } from "@testing/mock-services";
import { ContainerTemplate } from "../../../../../services/container/container.service";
import { TemplateAddedTokenRowComponent } from "../../container-template-edit-page/template-added-token-row/template-added-token-row.component";
import { ContainerTemplateEditBodyComponent } from "./container-template-edit-body.component";

const baseTemplate: ContainerTemplate = {
  name: "Test",
  container_type: "generic",
  default: false,
  template_options: {
    tokens: [{ type: "hotp" } as any, { type: "totp" } as any]
  }
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
    const before = component["tokens"]().length;
    (component as any).onAddToken("hotp");
    expect(component["tokens"]().length).toBe(before + 1);
    expect((component["tokens"]()[before] as any).type).toBe("hotp");
    expect(component.template().template_options.tokens.length).toBe(before + 1);
    expect((component.template().template_options.tokens[before] as any).type).toBe("hotp");
  });

  it("onDeleteToken removes the token at the given index", () => {
    const before = component["tokens"]().length;
    (component as any).onDeleteToken(0);
    expect(component["tokens"]().length).toBe(before - 1);
    expect((component["tokens"]()[0] as any).type).toBe("totp");
    expect(component.template().template_options.tokens.length).toBe(before - 1);
    expect((component.template().template_options.tokens[0] as any).type).toBe("totp");
  });

  it("collectTokens aggregates every row's getCurrentPayload result", () => {
    const fakeRows = [
      { getCurrentPayload: () => ({ type: "hotp", user: false }) },
      { getCurrentPayload: () => ({ type: "totp", user: true }) }
    ] as unknown as readonly TemplateAddedTokenRowComponent[];
    Object.defineProperty(component, "tokenRows", { value: () => fakeRows });

    expect(component.collectTokens()).toEqual([
      { type: "hotp", user: false },
      { type: "totp", user: true }
    ]);
  });

  it("collectTokens returns null when any row's strategy form is invalid and iterates every row", () => {
    const validPayload: TokenEnrollmentPayload = { type: "hotp", user: false } as any;
    const validSpy = jest.fn(() => validPayload);
    const firstInvalidSpy = jest.fn(() => null);
    const secondInvalidSpy = jest.fn(() => null);
    const fakeRows = [
      { getCurrentPayload: validSpy },
      { getCurrentPayload: firstInvalidSpy },
      { getCurrentPayload: secondInvalidSpy }
    ] as unknown as readonly TemplateAddedTokenRowComponent[];
    Object.defineProperty(component, "tokenRows", { value: () => fakeRows });

    expect(component.collectTokens()).toBeNull();
    // All rows are queried even after the first invalid one, so every offending row's strategy
    // has its forms marked as touched.
    expect(validSpy).toHaveBeenCalledTimes(1);
    expect(firstInvalidSpy).toHaveBeenCalledTimes(1);
    expect(secondInvalidSpy).toHaveBeenCalledTimes(1);
  });

  it("scrollToFirstInvalid scrolls to the first invalid row captured during collectTokens", () => {
    const scrollSpy = jest.fn();
    const fakeRows = [
      { getCurrentPayload: () => ({ type: "hotp", user: false }), scrollIntoView: jest.fn() },
      { getCurrentPayload: () => null, scrollIntoView: scrollSpy },
      { getCurrentPayload: () => null, scrollIntoView: jest.fn() }
    ] as unknown as readonly TemplateAddedTokenRowComponent[];
    Object.defineProperty(component, "tokenRows", { value: () => fakeRows });

    component.collectTokens();
    component.scrollToFirstInvalid();

    expect(scrollSpy).toHaveBeenCalledTimes(1);
    expect((fakeRows[2] as any).scrollIntoView).not.toHaveBeenCalled();
  });

  it("scrollToFirstInvalid is a no-op when collectTokens succeeded", () => {
    const r0 = { getCurrentPayload: () => ({ type: "hotp", user: false }), scrollIntoView: jest.fn() };
    const r1 = { getCurrentPayload: () => ({ type: "totp", user: false }), scrollIntoView: jest.fn() };
    Object.defineProperty(component, "tokenRows", {
      value: () => [r0, r1] as unknown as readonly TemplateAddedTokenRowComponent[]
    });

    expect(component.collectTokens()).not.toBeNull();
    component.scrollToFirstInvalid();
    expect(r0.scrollIntoView).not.toHaveBeenCalled();
    expect(r1.scrollIntoView).not.toHaveBeenCalled();
  });
});
