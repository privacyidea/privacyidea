import {ComponentFixture, TestBed} from '@angular/core/testing';

import {ContainerTableComponent} from './container-table.component';
import {provideHttpClient} from '@angular/common/http';
import {provideHttpClientTesting} from '@angular/common/http/testing';
import {BrowserAnimationsModule} from '@angular/platform-browser/animations';

describe('ContainerTableComponent', () => {
  let component: ContainerTableComponent;
  let fixture: ComponentFixture<ContainerTableComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ContainerTableComponent, BrowserAnimationsModule],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    })
      .compileComponents();

    fixture = TestBed.createComponent(ContainerTableComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
