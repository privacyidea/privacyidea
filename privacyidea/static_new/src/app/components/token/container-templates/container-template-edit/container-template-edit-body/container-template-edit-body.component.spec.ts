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
import { NoopAnimationsModule } from "@angular/platform-browser/animations";
import { ContainerTemplate } from "../../../../../services/container/container.service";
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
      imports: [ContainerTemplateEditBodyComponent, NoopAnimationsModule]
    }).compileComponents();

    fixture = TestBed.createComponent(ContainerTemplateEditBodyComponent);
    component = fixture.componentInstance;

    fixture.componentRef.setInput("template", { ...baseTemplate, template_options: { tokens: [...baseTemplate.template_options.tokens] } });
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
  });

  it("onDeleteToken removes the token at the given index", () => {
    const before = component["tokens"]().length;
    (component as any).onDeleteToken(0);
    expect(component["tokens"]().length).toBe(before - 1);
    expect((component["tokens"]()[0] as any).type).toBe("totp");
  });

  it("onEditToken merges a patch into the token at the given index", () => {
    (component as any).onEditToken({ description: "Edited" }, 0);
    expect((component["tokens"]()[0] as any).description).toBe("Edited");
    expect((component["tokens"]()[0] as any).type).toBe("hotp");
  });

  it("onEditToken removes undefined keys from the patched token", () => {
    (component as any).onEditToken({ type: undefined }, 0);
    expect("type" in component["tokens"]()[0]).toBe(false);
  });
});
