import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ContainerDetailsInfoComponent } from './container-details-info.component';
import {provideHttpClient} from '@angular/common/http';
import {provideHttpClientTesting} from '@angular/common/http/testing';
import {signal} from '@angular/core';

describe('ContainerDetailsInfoComponent', () => {
  let component: ContainerDetailsInfoComponent;
  let fixture: ComponentFixture<ContainerDetailsInfoComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ContainerDetailsInfoComponent],
      providers: [provideHttpClient(), provideHttpClientTesting()]
    })
    .compileComponents();

    fixture = TestBed.createComponent(ContainerDetailsInfoComponent);
    component = fixture.componentInstance;
    component.infoData = signal([]);
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
