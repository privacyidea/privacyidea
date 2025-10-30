import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ContainerTableActionsComponent } from './container-table-actions.component';
import { provideHttpClient } from "@angular/common/http";
import { provideHttpClientTesting } from "@angular/common/http/testing";

describe('ContainerTableActionsComponent', () => {
  let component: ContainerTableActionsComponent;
  let fixture: ComponentFixture<ContainerTableActionsComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
      imports: [ContainerTableActionsComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(ContainerTableActionsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
