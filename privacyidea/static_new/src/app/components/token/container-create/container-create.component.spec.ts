import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ContainerCreateComponent } from './container-create.component';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';

describe('ContainerCreateComponent', () => {
  let component: ContainerCreateComponent;
  let fixture: ComponentFixture<ContainerCreateComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ContainerCreateComponent, BrowserAnimationsModule],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();

    fixture = TestBed.createComponent(ContainerCreateComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
