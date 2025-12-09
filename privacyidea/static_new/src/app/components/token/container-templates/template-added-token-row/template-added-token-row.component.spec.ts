/**
 * (c) NetKnights GmbH 2025,  https://netknights.it
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
import { ContainerTemplateService } from "../../../../services/container-template/container-template.service";
import { NoopAnimationsModule } from "@angular/platform-browser/animations";
import { ContainerTemplateEditComponent } from "../container-template-edit/container-template-edit.component";
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { MockContainerTemplateService } from "../../../../../testing/mock-services/mock-container-template-service";
import { TemplateAddedTokenRowComponent } from "./template-added-token-row.component";

describe("TemplateAddedTokenRowComponent", () => {
  let component: TemplateAddedTokenRowComponent;
  let fixture: ComponentFixture<TemplateAddedTokenRowComponent>;
  let containerTemplateServiceMock: MockContainerTemplateService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TemplateAddedTokenRowComponent, NoopAnimationsModule, ContainerTemplateEditComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: ContainerTemplateService, useClass: MockContainerTemplateService }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(TemplateAddedTokenRowComponent);
    containerTemplateServiceMock = TestBed.inject(ContainerTemplateService) as unknown as MockContainerTemplateService;
    component = fixture.componentInstance;
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });

  it("updateToken should call editToken on containerTemplateService", () => {
    jest.spyOn(component.onEditToken, "emit");
    const tokenUpdate = { serial: "T-001", type: "totp" };
    component.updateToken(tokenUpdate);
    expect(component.onEditToken.emit).toHaveBeenCalledWith(tokenUpdate);
  });
  describe("onRemoveToken", () => {
    it("should call onRemoveToken emit with the correct token serial", () => {
      jest.spyOn(component.onRemoveToken, "emit");
      fixture.componentRef.setInput("index", 0);
      component.removeToken();
      expect(component.onRemoveToken.emit).toHaveBeenCalledWith(0);
    });

    it("should not call onRemoveToken emit if index is not valid", () => {
      jest.spyOn(component.onRemoveToken, "emit");
      fixture.componentRef.setInput("index", -1);
      component.removeToken();
      expect(component.onRemoveToken.emit).not.toHaveBeenCalled();
    });
  });
});
