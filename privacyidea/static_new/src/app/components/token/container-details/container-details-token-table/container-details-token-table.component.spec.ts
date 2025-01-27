import { ComponentFixture, TestBed } from '@angular/core/testing';
import { signal } from '@angular/core';
import { ContainerDetailsTokenTableComponent } from './container-details-token-table.component';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';

describe('ContainerDetailsTokenTableComponent', () => {
  let component: ContainerDetailsTokenTableComponent;
  let fixture: ComponentFixture<ContainerDetailsTokenTableComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ContainerDetailsTokenTableComponent, BrowserAnimationsModule],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();

    fixture = TestBed.createComponent(ContainerDetailsTokenTableComponent);
    component = fixture.componentInstance;
    component.dataSource = signal([]);
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
