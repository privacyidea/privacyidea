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

import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";
import { ComponentFixture, TestBed } from "@angular/core/testing";
import { NoopAnimationsModule } from "@angular/platform-browser/animations";
import { MockContainerTemplateService } from "../../../../../testing/mock-services";
import { ContainerTemplateService } from "../../../../services/container-template/container-template.service";
import { ContainerTemplateEditComponent } from "../dialogs/container-template-edit/container-template-edit.component";
import { ContainerTemplatesTableComponent } from "./container-templates-table.component";

describe("ContainerTemplatesComponent", () => {
  let component: ContainerTemplatesTableComponent;
  let fixture: ComponentFixture<ContainerTemplatesTableComponent>;
  let containerTemplateServiceMock: MockContainerTemplateService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ContainerTemplatesTableComponent, NoopAnimationsModule, ContainerTemplateEditComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: ContainerTemplateService, useClass: MockContainerTemplateService }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(ContainerTemplatesTableComponent);
    containerTemplateServiceMock = TestBed.inject(ContainerTemplateService) as unknown as MockContainerTemplateService;
    component = fixture.componentInstance;
  });

  it("should create", () => {
    expect(component).toBeTruthy();
  });
});
